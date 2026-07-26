import crypto from 'crypto';

export const TOTP_PERIOD_SECONDS = 30;

const BASE32_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';

const decodeBase32 = (input: string) => {
  const normalized = input.replace(/\s/g, '').replace(/=+$/, '').toUpperCase();
  const bytes: number[] = [];
  let bits = 0;
  let value = 0;

  for (const character of normalized) {
    const index = BASE32_ALPHABET.indexOf(character);
    if (index === -1) {
      throw new Error(`Invalid base32 character: ${character}`);
    }

    value = (value << 5) | index;
    bits += 5;

    if (bits >= 8) {
      bytes.push((value >>> (bits - 8)) & 0xff);
      bits -= 8;
    }
  }

  return Buffer.from(bytes);
};

export const makeTotpCode = (manualSecret: string) => {
  const counter = Math.floor(Date.now() / 1000 / TOTP_PERIOD_SECONDS);
  const counterBuffer = Buffer.alloc(8);
  counterBuffer.writeBigUInt64BE(BigInt(counter));
  const digest = crypto.createHmac('sha1', decodeBase32(manualSecret)).update(counterBuffer).digest();
  const offset = digest[digest.length - 1] & 0x0f;
  const truncatedHash = digest.readUInt32BE(offset) & 0x7fffffff;
  return String(truncatedHash % 1_000_000).padStart(6, '0');
};
