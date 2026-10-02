// Whether the user has an active subscription. A subscription that is still awaiting payment verification doesn't count.
export const hasActiveSubscription = (): boolean =>
  !window._page?.isAwaitingPaymentVerification && Boolean(window._page?.hasActiveSubscription);

export const hasAcceptedTos = (): boolean => !window._page?.needsTosAcceptance;
