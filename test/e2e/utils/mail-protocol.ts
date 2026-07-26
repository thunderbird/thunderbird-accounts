import net from 'net';
import tls from 'tls';
import { expect } from '@playwright/test';

import {
  ACCTS_HOST,
  IMAP_PORT,
  PRIMARY_THUNDERMAIL_EMAIL,
  SMTP_PORT,
  SMTP_TLS,
  TIMEOUT_30_SECONDS,
} from '../const/constants';

const readUntil = async (socket: net.Socket, isComplete: (buffer: string) => boolean) =>
  new Promise<string>((resolve, reject) => {
    let buffer = '';
    const timeout = setTimeout(() => {
      cleanup();
      reject(new Error(`Timed out waiting for mail server response. Last response: ${buffer}`));
    }, TIMEOUT_30_SECONDS);
    const cleanup = () => {
      clearTimeout(timeout);
      socket.off('data', onData);
      socket.off('error', onError);
    };
    const onData = (data: Buffer) => {
      buffer += data.toString('utf8');
      if (isComplete(buffer)) {
        cleanup();
        resolve(buffer);
      }
    };
    const onError = (error: Error) => {
      cleanup();
      reject(error);
    };

    socket.on('data', onData);
    socket.on('error', onError);
  });

const isTlsEnabled = (value: string) => !['false', 'none', 'undefined', ''].includes(value.toLowerCase());

// Local e2e connects to the dev mail server, which presents a self-signed certificate.
// This client only ever talks to the local stack (ACCTS_HOST), so chain verification is
// opt-out via an explicit env flag (defaults to allowing the dev cert). Never set this
// against production.
const VERIFY_MAIL_SERVER_TLS = String(process.env.E2E_VERIFY_MAIL_TLS ?? 'false') === 'true';

const connectToMailServer = async (port: number, useTls = false) =>
  new Promise<net.Socket>((resolve, reject) => {
    const socket = useTls
      ? tls.connect({ host: ACCTS_HOST, port, rejectUnauthorized: VERIFY_MAIL_SERVER_TLS }, () => resolve(socket))
      : net.createConnection({ host: ACCTS_HOST, port }, () => resolve(socket));
    socket.setTimeout(TIMEOUT_30_SECONDS);
    socket.once('error', reject);
    socket.once('timeout', () => {
      socket.destroy();
      reject(new Error(`Timed out connecting to ${ACCTS_HOST}:${port}`));
    });
  });

const writeAndRead = async (
  socket: net.Socket,
  command: string,
  isComplete: (buffer: string) => boolean,
) => {
  socket.write(command);
  return readUntil(socket, isComplete);
};

const makeXoauth2Payload = (accessToken: string) =>
  Buffer.from(`user=${PRIMARY_THUNDERMAIL_EMAIL}\x01auth=Bearer ${accessToken}\x01\x01`).toString('base64');

export const expectImapXoauth2Login = async (accessToken: string) => {
  const socket = await connectToMailServer(IMAP_PORT);
  const authPayload = makeXoauth2Payload(accessToken);

  try {
    await readUntil(socket, (response) => response.includes('* OK'));
    const authResponse = await writeAndRead(
      socket,
      `a1 AUTHENTICATE XOAUTH2 ${authPayload}\r\n`,
      (response) => /a1 (OK|NO|BAD)/i.test(response),
    );
    expect(authResponse).toMatch(/a1 OK/i);
    await writeAndRead(socket, 'a2 LOGOUT\r\n', (response) => /a2 OK/i.test(response));
  } finally {
    socket.destroy();
  }
};

export const expectSmtpXoauth2Login = async (accessToken: string) => {
  const socket = await connectToMailServer(SMTP_PORT, isTlsEnabled(SMTP_TLS));
  const authPayload = makeXoauth2Payload(accessToken);

  try {
    await readUntil(socket, (response) => /^220/m.test(response));
    await writeAndRead(socket, 'EHLO tb-accounts-e2e.example.org\r\n', (response) => /\r?\n250[ -]/.test(response));
    const authResponse = await writeAndRead(
      socket,
      `AUTH XOAUTH2 ${authPayload}\r\n`,
      (response) => /^(235|334|535|454)/m.test(response),
    );
    expect(authResponse).toMatch(/^235/m);
    await writeAndRead(socket, 'QUIT\r\n', (response) => /^221/m.test(response));
  } finally {
    socket.destroy();
  }
};
