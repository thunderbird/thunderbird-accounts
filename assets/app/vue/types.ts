/* Source: https://docs.djangoproject.com/en/5.2/ref/contrib/messages/#creating-custom-message-levels */
export enum SERVER_MESSAGE_LEVEL {
  DEBUG = 10,
  INFO = 20,
  SUCCESS = 25,
  WARNING = 30,
  ERROR = 40,
}

export type ServerMessage = {
  level: SERVER_MESSAGE_LEVEL;
  message: string;
};