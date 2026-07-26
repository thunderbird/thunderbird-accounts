import { TELEMETRY_EVENTS } from "@/types";
import { SIGN_UP_STEPS, SIGN_UP_STEPS_TO_STR } from "./stores/signUpFlowStore";
import { CAPTURE_TELEMETRY } from "@/defines";

/**
 * Send the telemetry event to the server. This should not block!
 */
const sendTelemetryEvent = (event: TELEMETRY_EVENTS, properties: object | null = null) => {
  if (!CAPTURE_TELEMETRY) {
    return;
  }
  fetch('/api/v1/telemetry/event', {
    method: 'POST',
    body: JSON.stringify({
      event,
      event_properties: properties || null,
    }),
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': window._page?.csrfToken,
    },
  });
}

export const captureSupportLinkClick = () => {
  sendTelemetryEvent(TELEMETRY_EVENTS.SIGN_UP_SUPPORT)
};

export const captureError = (error_string: string) => {
  sendTelemetryEvent(TELEMETRY_EVENTS.SIGN_UP_ERROR, { 'error': error_string });
};

export const captureStep = (sign_up_step: SIGN_UP_STEPS) => {
  sendTelemetryEvent(TELEMETRY_EVENTS.SIGN_UP_STEP, { 'step_num': sign_up_step, 'step_str': SIGN_UP_STEPS_TO_STR[sign_up_step] || SIGN_UP_STEPS_TO_STR[SIGN_UP_STEPS.INVALID] })
};
