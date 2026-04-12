import React, { useMemo } from 'react';
import SwaggerUI from 'swagger-ui-react';
import { parse } from 'yaml';
import editorCssUrl from 'swagger-editor-dist/swagger-editor.css?url';
import editorBundleUrl from 'swagger-editor-dist/swagger-editor-bundle.js?url';
import editorPresetUrl from 'swagger-editor-dist/swagger-editor-standalone-preset.js?url';
import 'swagger-ui-react/swagger-ui.css';

function getParseErrorMessage(error) {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return 'OpenAPI YAML 解析失败。';
}

function serializeForInlineScript(value) {
  return JSON.stringify(value).replace(/</g, '\\u003c');
}

function buildSwaggerEditorDoc(specObject) {
  const specJson = serializeForInlineScript(specObject);

  return `<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Swagger Editor</title>
    <link rel="stylesheet" href="${editorCssUrl}" />
    <style>
      html, body, #swagger-editor {
        height: 100%;
        margin: 0;
      }

      body {
        background: #f8fafc;
      }

      .swagger-editor {
        height: 100%;
      }
    </style>
  </head>
  <body>
    <div id="swagger-editor"></div>
    <script src="${editorBundleUrl}"></script>
    <script src="${editorPresetUrl}"></script>
    <script>
      window.onload = function () {
        window.editor = SwaggerEditorBundle({
          dom_id: '#swagger-editor',
          spec: ${specJson},
          layout: 'StandaloneLayout',
          presets: [SwaggerEditorStandalonePreset]
        });
      };
    </script>
  </body>
</html>`;
}

function OpenApiErrorState({ message }) {
  return (
    <div className="openapi-error">
      <div className="openapi-error__title">OpenAPI 渲染失败</div>
      <p className="openapi-error__message">{message}</p>
    </div>
  );
}

export default function OpenApiRenderer({ content, mode }) {
  const { specObject, errorMessage } = useMemo(() => {
    try {
      return {
        specObject: parse(content),
        errorMessage: ''
      };
    } catch (error) {
      return {
        specObject: null,
        errorMessage: getParseErrorMessage(error)
      };
    }
  }, [content]);

  if (errorMessage) {
    return <OpenApiErrorState message={errorMessage} />;
  }

  if (!specObject) {
    return <OpenApiErrorState message="当前 OpenAPI 文档为空。" />;
  }

  if (mode === 'editor') {
    return (
      <section className="openapi-shell">
        <div className="openapi-shell__hint">
          Swagger Editor 视图基于当前 YAML 即时生成，支持在浏览器中检查结构与交互式编辑效果。
        </div>
        <iframe
          title="Swagger Editor"
          className="swagger-editor-frame"
          sandbox="allow-scripts allow-same-origin"
          srcDoc={buildSwaggerEditorDoc(specObject)}
        />
      </section>
    );
  }

  return (
    <section className="openapi-shell">
      <SwaggerUI
        spec={specObject}
        deepLinking
        displayOperationId
        defaultModelsExpandDepth={-1}
        docExpansion="list"
        tryItOutEnabled={false}
      />
    </section>
  );
}
