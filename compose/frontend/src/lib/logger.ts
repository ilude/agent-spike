/**
 * Structured logging for frontend with SigNoz integration
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LogEntry {
  timestamp: string;
  level: LogLevel;
  message: string;
  service: string;
  context?: Record<string, any>;
  correlation_id?: string;
  user_id?: string;
  error?: {
    name?: string;
    message?: string;
    stack?: string;
  };
}

class Logger {
  private correlationId?: string;
  private userId?: string;
  private serviceName: string = 'mentat-frontend';

  /**
   * Set correlation ID for all subsequent logs
   */
  setCorrelationId(id: string) {
    this.correlationId = id;
  }

  /**
   * Set user ID for all subsequent logs
   */
  setUserId(id: string) {
    this.userId = id;
  }

  /**
   * Clear correlation ID
   */
  clearCorrelationId() {
    this.correlationId = undefined;
  }

  /**
   * Log a message with structured context
   */
  private log(
    level: LogLevel,
    message: string,
    context?: Record<string, any>,
    error?: Error
  ) {
    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level,
      message,
      service: this.serviceName,
      ...(context && { context }),
      ...(this.correlationId && { correlation_id: this.correlationId }),
      ...(this.userId && { user_id: this.userId }),
    };

    // Add error details if present
    if (error) {
      entry.error = {
        name: error.name,
        message: error.message,
        stack: error.stack,
      };
    }

    // Output to console with color coding
    const consoleMethod = level === 'error' ? 'error' : level === 'warn' ? 'warn' : 'log';
    console[consoleMethod](JSON.stringify(entry));

    // Send critical logs to backend for aggregation
    if (level === 'error' || level === 'warn') {
      this.sendToBackend(entry);
    }
  }

  /**
   * Send log entry to backend API for aggregation
   */
  private async sendToBackend(entry: LogEntry) {
    try {
      // Use beacon API for reliability (works even if page is closing)
      const blob = new Blob([JSON.stringify(entry)], {
        type: 'application/json',
      });

      if (navigator.sendBeacon) {
        navigator.sendBeacon('https://api.local.ilude.com/logs', blob);
      } else {
        // Fallback to fetch
        fetch('https://api.local.ilude.com/logs', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(entry),
          keepalive: true,
        }).catch(() => {
          // Silently fail - don't want logging errors to break the app
        });
      }
    } catch {
      // Silently fail
    }
  }

  /**
   * Log debug message (development only)
   */
  debug(message: string, context?: Record<string, any>) {
    if (import.meta.env.DEV) {
      this.log('debug', message, context);
    }
  }

  /**
   * Log info message
   */
  info(message: string, context?: Record<string, any>) {
    this.log('info', message, context);
  }

  /**
   * Log warning message
   */
  warn(message: string, context?: Record<string, any>) {
    this.log('warn', message, context);
  }

  /**
   * Log error message
   */
  error(message: string, contextOrError?: Record<string, any> | Error, error?: Error) {
    // Handle both signatures: error(msg, context, error) and error(msg, error)
    if (contextOrError instanceof Error) {
      this.log('error', message, undefined, contextOrError);
    } else {
      this.log('error', message, contextOrError, error);
    }
  }

  /**
   * Log API call with timing
   */
  async logApiCall<T>(
    endpoint: string,
    method: string,
    apiCall: () => Promise<T>
  ): Promise<T> {
    const startTime = performance.now();
    const context = { endpoint, method };

    try {
      this.debug(`API call started: ${method} ${endpoint}`, context);
      const result = await apiCall();
      const duration = performance.now() - startTime;

      this.debug(`API call completed: ${method} ${endpoint}`, {
        ...context,
        duration_ms: duration.toFixed(2),
        status: 'success',
      });

      return result;
    } catch (error) {
      const duration = performance.now() - startTime;

      this.error(
        `API call failed: ${method} ${endpoint}`,
        {
          ...context,
          duration_ms: duration.toFixed(2),
          status: 'error',
        },
        error instanceof Error ? error : new Error(String(error))
      );

      throw error;
    }
  }
}

// Export singleton instance
export const logger = new Logger();

// Setup global error handler
if (typeof window !== 'undefined') {
  window.addEventListener('error', (event) => {
    logger.error('Uncaught error', {
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno,
    }, event.error);
  });

  window.addEventListener('unhandledrejection', (event) => {
    logger.error('Unhandled promise rejection', {
      reason: event.reason,
    });
  });
}
