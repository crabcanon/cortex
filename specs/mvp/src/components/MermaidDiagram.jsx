import React, { useEffect, useId, useState } from 'react';
import mermaid from 'mermaid';

let mermaidReady = false;

function ensureMermaid() {
  if (mermaidReady) {
    return;
  }

  mermaid.initialize({
    startOnLoad: false,
    theme: 'neutral',
    securityLevel: 'loose',
    fontFamily: '"PingFang SC", "Microsoft YaHei", "Noto Sans SC", sans-serif'
  });

  mermaidReady = true;
}

function getErrorMessage(error) {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return 'Mermaid 图表解析失败，请检查语法。';
}

export default function MermaidDiagram({ chart }) {
  const elementId = useId().replace(/:/g, '-');
  const [svg, setSvg] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    let cancelled = false;

    async function renderChart() {
      ensureMermaid();

      try {
        const { svg: renderedSvg } = await mermaid.render(`ordix-mermaid-${elementId}`, chart.trim());

        if (!cancelled) {
          setSvg(renderedSvg);
          setErrorMessage('');
        }
      } catch (error) {
        if (!cancelled) {
          setSvg('');
          setErrorMessage(getErrorMessage(error));
        }
      }
    }

    if (chart.trim()) {
      renderChart();
    } else {
      setSvg('');
      setErrorMessage('');
    }

    return () => {
      cancelled = true;
    };
  }, [chart, elementId]);

  if (errorMessage) {
    return (
      <div className="mermaid-error">
        <div className="mermaid-error__title">Mermaid 渲染失败</div>
        <p className="mermaid-error__message">{errorMessage}</p>
        <pre className="mermaid-error__source">{chart}</pre>
      </div>
    );
  }

  if (!svg) {
    return (
      <div className="mermaid-loading">
        正在渲染 Mermaid 图表...
      </div>
    );
  }

  return <div className="mermaid-diagram" dangerouslySetInnerHTML={{ __html: svg }} />;
}
