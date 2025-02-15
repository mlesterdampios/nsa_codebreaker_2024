// logger.ts

const logLevels = {
  DEBUG: 0,
  INFO: 1,
  WARNING: 2,
  ERROR: 3,
  CRITICAL: 4,
};

let currentLevel = logLevels.INFO;

function logMessage(level: string, ...args: unknown[]) {
  if (logLevels[level as keyof typeof logLevels] < currentLevel) return;

  const message = JSON.stringify({
    t: new Date().toISOString(),
    l: level,
    m: args.join(' '),
  });

  if (level === 'ERROR' || level === 'CRITICAL') {
    console.error(message);
  } else {
    console.log(message);
  }
}

export const logger = {
  debug: (...args: unknown[]) => logMessage('DEBUG', ...args),
  info: (...args: unknown[]) => logMessage('INFO', ...args),
  warning: (...args: unknown[]) => logMessage('WARNING', ...args),
  error: (...args: unknown[]) => logMessage('ERROR', ...args),
  critical: (...args: unknown[]) => logMessage('CRITICAL', ...args),
};

export function assert(condition: boolean, message?: string): asserts condition {
  if (!condition) {
    throw new Error(message || 'Assertion failed');
  }
}