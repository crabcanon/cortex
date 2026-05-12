"use client";

import { useEffect, useRef, useState } from "react";

declare global {
  interface Window {
    SwaggerUIBundle?: SwaggerUIBundleFactory;
    SwaggerUIStandalonePreset?: unknown;
  }
}

type SwaggerUIBundleFactory = {
  (options: Record<string, unknown>): unknown;
  presets: {
    apis: unknown;
  };
};

type CortexSwaggerUiProps = {
  specUrl: string;
};

const swaggerBase = "/vendor/swagger-ui";

function loadStylesheet(href: string) {
  return new Promise<void>((resolve, reject) => {
    const existing = document.querySelector<HTMLLinkElement>(
      `link[data-cortex-swagger-css="${href}"]`,
    );

    if (existing) {
      resolve();
      return;
    }

    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = href;
    link.dataset.cortexSwaggerCss = href;
    link.onload = () => resolve();
    link.onerror = () => reject(new Error(`Failed to load stylesheet: ${href}`));
    document.head.appendChild(link);
  });
}

function loadScript(src: string) {
  return new Promise<void>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(
      `script[data-cortex-swagger-script="${src}"]`,
    );

    if (existing) {
      if (existing.dataset.loaded === "true") {
        resolve();
        return;
      }

      existing.addEventListener("load", () => resolve(), { once: true });
      existing.addEventListener(
        "error",
        () => reject(new Error(`Failed to load script: ${src}`)),
        { once: true },
      );
      return;
    }

    const script = document.createElement("script");
    script.src = src;
    script.async = false;
    script.dataset.cortexSwaggerScript = src;
    script.onload = () => {
      script.dataset.loaded = "true";
      resolve();
    };
    script.onerror = () => reject(new Error(`Failed to load script: ${src}`));
    document.body.appendChild(script);
  });
}

export default function CortexSwaggerUi({ specUrl }: CortexSwaggerUiProps) {
  const mounted = useRef(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    mounted.current = true;

    async function bootstrap() {
      try {
        setError(null);
        await loadStylesheet(`${swaggerBase}/swagger-ui.css`);
        await loadScript(`${swaggerBase}/swagger-ui-bundle.js`);
        await loadScript(`${swaggerBase}/swagger-ui-standalone-preset.js`);

        if (!mounted.current) return;
        if (!window.SwaggerUIBundle || !window.SwaggerUIStandalonePreset) {
          throw new Error("Swagger UI runtime was not initialized.");
        }

        window.SwaggerUIBundle({
          url: specUrl,
          dom_id: "#swagger-ui",
          deepLinking: true,
          displayRequestDuration: true,
          docExpansion: "none",
          persistAuthorization: true,
          validatorUrl: null,
          presets: [
            window.SwaggerUIBundle.presets.apis,
            window.SwaggerUIStandalonePreset,
          ],
          layout: "StandaloneLayout",
        });
      } catch (err) {
        if (!mounted.current) return;
        setError(err instanceof Error ? err.message : String(err));
      }
    }

    void bootstrap();

    return () => {
      mounted.current = false;
    };
  }, [specUrl]);

  return (
    <main className="min-h-screen bg-white text-slate-950">
      {error ? (
        <div className="mx-auto max-w-3xl px-6 py-10">
          <h1 className="text-2xl font-semibold">Swagger UI 加载失败</h1>
          <p className="mt-4 text-sm text-slate-700">{error}</p>
          <p className="mt-4 text-sm text-slate-700">
            你仍然可以直接下载 OpenAPI YAML：
            <a className="ml-1 underline" href={specUrl}>
              {specUrl}
            </a>
          </p>
        </div>
      ) : null}
      <div id="swagger-ui" />
    </main>
  );
}
