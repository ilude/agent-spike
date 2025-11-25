/**
 * OpenTelemetry browser tracing for SigNoz
 */

import { WebTracerProvider } from '@opentelemetry/sdk-trace-web';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { BatchSpanProcessor } from '@opentelemetry/sdk-trace-base';
import { registerInstrumentations } from '@opentelemetry/instrumentation';
import { FetchInstrumentation } from '@opentelemetry/instrumentation-fetch';
import { Resource } from '@opentelemetry/resources';
import { SemanticResourceAttributes } from '@opentelemetry/semantic-conventions';

let isSetup = false;

/**
 * Setup OpenTelemetry browser tracing
 *
 * This configures automatic instrumentation for:
 * - fetch() API calls
 * - XHR requests
 * - User interactions (future)
 */
export function setupTelemetry() {
  // Prevent double initialization
  if (isSetup) {
    console.warn('Telemetry already initialized');
    return;
  }

  try {
    // Create resource with service metadata
    const resource = new Resource({
      [SemanticResourceAttributes.SERVICE_NAME]: 'mentat-frontend',
      [SemanticResourceAttributes.SERVICE_NAMESPACE]: 'agent-spike',
      [SemanticResourceAttributes.DEPLOYMENT_ENVIRONMENT]: import.meta.env.MODE || 'production',
    });

    // Create trace provider
    const provider = new WebTracerProvider({
      resource,
    });

    // Create OTLP exporter (send traces to SigNoz via API proxy)
    const exporter = new OTLPTraceExporter({
      url: 'https://api.local.ilude.com/v1/traces',
      headers: {},
    });

    // Add batch processor for efficient export
    provider.addSpanProcessor(new BatchSpanProcessor(exporter, {
      maxQueueSize: 100,
      scheduledDelayMillis: 5000, // Export every 5 seconds
    }));

    // Register provider
    provider.register();

    // Auto-instrument fetch API
    registerInstrumentations({
      instrumentations: [
        new FetchInstrumentation({
          // Propagate trace context to backend
          propagateTraceHeaderCorsUrls: [
            /https:\/\/api\.local\.ilude\.com.*/,
            /http:\/\/localhost:8000.*/,
          ],
          // Ignore health check and stats polling
          ignoreUrls: [
            /\/stats\/stream/,
            /\/health/,
          ],
          // Add custom attributes to spans
          applyCustomAttributesOnSpan: (span, request, response) => {
            // Add correlation ID from response
            if (response && response.headers) {
              const correlationId = response.headers.get('X-Correlation-ID');
              if (correlationId) {
                span.setAttribute('correlation_id', correlationId);
              }
            }
          },
        }),
      ],
    });

    isSetup = true;
    console.log('✅ OpenTelemetry browser tracing initialized');
  } catch (error) {
    console.error('❌ Failed to initialize telemetry:', error);
  }
}

/**
 * Manually create a span for custom operations
 *
 * @example
 * const span = createSpan('user_action', { action: 'submit_form' });
 * try {
 *   await doSomething();
 * } finally {
 *   span.end();
 * }
 */
export function createSpan(name: string, attributes: Record<string, string | number> = {}) {
  const tracer = provider.getTracer('mentat-frontend');
  const span = tracer.startSpan(name);

  // Add attributes
  Object.entries(attributes).forEach(([key, value]) => {
    span.setAttribute(key, value);
  });

  return span;
}
