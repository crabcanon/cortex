"use client";

import type { PointerEvent, WheelEvent } from "react";
import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import {
  Download,
  FileImage,
  Maximize,
  Maximize2,
  Minimize2,
  RotateCcw,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import { useTheme } from "next-themes";
import styles from "./Mermaid.module.scss";

type MermaidRenderResult = {
  svg: string;
  bindFunctions?: (element: Element) => void;
};

type MermaidProps = {
  chart: string;
};

type SvgSize = {
  width: number;
  height: number;
};

type ViewState = {
  scale: number;
  x: number;
  y: number;
};

type DragState = {
  pointerId: number;
  x: number;
  y: number;
  view: ViewState;
};

type ZoomOrigin = {
  x: number;
  y: number;
};

const MIN_SCALE = 0.15;
const MAX_SCALE = 3;
const SCALE_STEP = 0.2;
const WHEEL_ZOOM_SENSITIVITY = 0.0015;
const VIEW_PADDING = 24;
const EXPORT_PIXEL_RATIO = 2;
const MAX_EXPORT_DIMENSION = 16384;
const MAX_EXPORT_PIXELS = 16_000_000;
const SVG_NS = "http://www.w3.org/2000/svg";
const XLINK_NS = "http://www.w3.org/1999/xlink";
const XHTML_NS = "http://www.w3.org/1999/xhtml";

const Mermaid: React.FC<MermaidProps> = ({ chart }) => {
  const id = useId().replace(/:/g, "");
  const viewerRef = useRef<HTMLDivElement>(null);
  const viewportRef = useRef<HTMLDivElement>(null);
  const diagramRef = useRef<HTMLDivElement>(null);
  const dragStateRef = useRef<DragState | null>(null);
  const viewRef = useRef<ViewState>({ scale: 1, x: 0, y: 0 });
  const { resolvedTheme } = useTheme();
  const [result, setResult] = useState<MermaidRenderResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [view, setViewState] = useState<ViewState>(viewRef.current);
  const [svgSize, setSvgSize] = useState<SvgSize | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [isExportingPng, setIsExportingPng] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const normalizedChart = useMemo(() => chart.replaceAll("\\n", "\n"), [chart]);
  const filenameBase = useMemo(
    () => `mermaid-${hashString(normalizedChart)}`,
    [normalizedChart]
  );

  const setView = useCallback((next: ViewState) => {
    const clamped = {
      ...next,
      scale: clampScale(roundScale(next.scale)),
    };
    viewRef.current = clamped;
    setViewState(clamped);
  }, []);

  const fitToCanvas = useCallback(() => {
    const viewport = viewportRef.current;
    const size = svgSize;
    if (!viewport || !size) return;

    const availableWidth = Math.max(1, viewport.clientWidth - VIEW_PADDING * 2);
    const scale = clampScale(roundScale(Math.min(1, availableWidth / size.width)));

    setView(centerView({ viewport, size, scale }));
  }, [setView, svgSize]);

  useEffect(() => {
    let cancelled = false;

    async function renderChart() {
      try {
        const mermaid = (await import("mermaid")).default;

        mermaid.initialize({
          startOnLoad: false,
          securityLevel: "loose",
          fontFamily: "inherit",
          theme: resolvedTheme === "dark" ? "dark" : "default",
        });

        const renderResult = await mermaid.render(
          `mermaid-${id}-${resolvedTheme ?? "light"}`,
          normalizedChart
        );

        if (!cancelled) {
          setError(null);
          setExportError(null);
          setSvgSize(null);
          setView({ scale: 1, x: VIEW_PADDING, y: VIEW_PADDING });
          setResult({
            svg: renderResult.svg,
            bindFunctions: renderResult.bindFunctions,
          });
        }
      } catch (cause) {
        if (!cancelled) {
          setResult(null);
          setError(
            cause instanceof Error
              ? cause.message
              : "Mermaid diagram failed to render."
          );
        }
      }
    }

    void renderChart();

    return () => {
      cancelled = true;
    };
  }, [id, normalizedChart, resolvedTheme, setView]);

  useEffect(() => {
    const diagram = diagramRef.current;
    if (!diagram || !result) return;

    const svg = diagram.querySelector("svg");
    if (svg instanceof SVGSVGElement) {
      const size = readSvgSize(svg);
      setSvgSize(size);

      svg.style.display = "block";
      svg.style.maxWidth = "none";
      svg.style.maxHeight = "none";
      svg.style.width = `${Math.max(1, size.width)}px`;
      svg.style.height = `${Math.max(1, size.height)}px`;
      svg.style.margin = "0";
    }

    result.bindFunctions?.(diagram);
  }, [result]);

  useEffect(() => {
    if (!svgSize) return;

    const frame = window.requestAnimationFrame(fitToCanvas);
    return () => window.cancelAnimationFrame(frame);
  }, [fitToCanvas, svgSize]);

  useEffect(() => {
    const syncFullscreen = () => {
      const active = document.fullscreenElement === viewerRef.current;
      setIsFullscreen(active);
      if (active) {
        window.requestAnimationFrame(fitToCanvas);
      }
    };

    document.addEventListener("fullscreenchange", syncFullscreen);
    return () => document.removeEventListener("fullscreenchange", syncFullscreen);
  }, [fitToCanvas]);

  useEffect(() => {
    if (!isFullscreen) return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        void exitFullscreen();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isFullscreen]);

  const zoomTo = useCallback(
    (scale: number, origin?: ZoomOrigin) => {
      const viewport = viewportRef.current;
      const current = viewRef.current;
      const nextScale = clampScale(roundScale(scale));

      if (!viewport) {
        setView({ ...current, scale: nextScale });
        return;
      }

      const anchorX = origin?.x ?? viewport.clientWidth / 2;
      const anchorY = origin?.y ?? viewport.clientHeight / 2;
      const contentX = (anchorX - current.x) / current.scale;
      const contentY = (anchorY - current.y) / current.scale;

      setView({
        scale: nextScale,
        x: anchorX - contentX * nextScale,
        y: anchorY - contentY * nextScale,
      });
    },
    [setView]
  );

  const actualSize = useCallback(() => {
    const viewport = viewportRef.current;
    const size = svgSize;
    if (!viewport || !size) {
      setView({ scale: 1, x: VIEW_PADDING, y: VIEW_PADDING });
      return;
    }

    setView(centerView({ viewport, size, scale: 1 }));
  }, [setView, svgSize]);

  const toggleFullscreen = useCallback(async () => {
    if (document.fullscreenElement) {
      await exitFullscreen();
      return;
    }

    const viewer = viewerRef.current;
    if (!viewer?.requestFullscreen) {
      setIsFullscreen(true);
      window.requestAnimationFrame(fitToCanvas);
      return;
    }

    await viewer.requestFullscreen();
  }, [fitToCanvas]);

  const getExportSvg = useCallback(() => {
    const svg = diagramRef.current?.querySelector("svg");
    if (!(svg instanceof SVGSVGElement)) return null;

    const size = svgSize ?? readSvgSize(svg);

    return {
      markup: serializeSvgForExport(svg, size),
      size,
    };
  }, [svgSize]);

  const downloadSvg = useCallback(() => {
    const exported = getExportSvg();
    if (!exported) return;

    downloadBlob(
      new Blob([exported.markup], {
        type: "image/svg+xml;charset=utf-8",
      }),
      `${filenameBase}.svg`
    );
  }, [filenameBase, getExportSvg]);

  const downloadPng = useCallback(async () => {
    if (isExportingPng) return;

    const exported = getExportSvg();
    if (!exported) return;

    setIsExportingPng(true);
    setExportError(null);

    try {
      const image = await loadImage(svgToDataUrl(exported.markup));
      const exportScale = getExportScale(exported.size);
      const canvas = document.createElement("canvas");
      canvas.width = Math.max(1, Math.ceil(exported.size.width * exportScale));
      canvas.height = Math.max(1, Math.ceil(exported.size.height * exportScale));

      const context = canvas.getContext("2d");
      if (!context) {
        throw new Error("Canvas context is not available.");
      }

      context.fillStyle = resolvedTheme === "dark" ? "#1f1f1f" : "#ffffff";
      context.fillRect(0, 0, canvas.width, canvas.height);
      context.drawImage(image, 0, 0, canvas.width, canvas.height);

      const pngBlob = await new Promise<Blob | null>((resolve) => {
        canvas.toBlob(resolve, "image/png");
      });
      if (!pngBlob) {
        throw new Error("Canvas failed to create a PNG blob.");
      }

      downloadBlob(pngBlob, `${filenameBase}.png`);
    } catch (cause) {
      console.warn("Failed to export Mermaid PNG.", cause);
      setExportError("PNG export failed. SVG export is still available.");
    } finally {
      setIsExportingPng(false);
    }
  }, [filenameBase, getExportSvg, isExportingPng, resolvedTheme]);

  const handlePointerDown = useCallback(
    (event: PointerEvent<HTMLDivElement>) => {
      if (event.button !== 0) return;

      const viewport = viewportRef.current;
      if (!viewport) return;

      event.preventDefault();
      dragStateRef.current = {
        pointerId: event.pointerId,
        x: event.clientX,
        y: event.clientY,
        view: viewRef.current,
      };
      viewport.setPointerCapture(event.pointerId);
      setIsDragging(true);
    },
    []
  );

  const handlePointerMove = useCallback(
    (event: PointerEvent<HTMLDivElement>) => {
      const dragState = dragStateRef.current;
      if (!dragState) return;

      event.preventDefault();
      setView({
        ...dragState.view,
        x: dragState.view.x + event.clientX - dragState.x,
        y: dragState.view.y + event.clientY - dragState.y,
      });
    },
    [setView]
  );

  const endDrag = useCallback((event: PointerEvent<HTMLDivElement>) => {
    const dragState = dragStateRef.current;
    const viewport = viewportRef.current;
    if (dragState && viewport?.hasPointerCapture(dragState.pointerId)) {
      viewport.releasePointerCapture(dragState.pointerId);
    } else if (viewport?.hasPointerCapture(event.pointerId)) {
      viewport.releasePointerCapture(event.pointerId);
    }
    dragStateRef.current = null;
    setIsDragging(false);
  }, []);

  const handleWheel = useCallback(
    (event: WheelEvent<HTMLDivElement>) => {
      const viewport = viewportRef.current;
      if (!viewport) return;

      event.preventDefault();
      const rect = viewport.getBoundingClientRect();
      const normalizedDelta = normalizeWheelDelta(event, viewport.clientHeight);
      const scaleFactor = Math.exp(-normalizedDelta * WHEEL_ZOOM_SENSITIVITY);

      zoomTo(viewRef.current.scale * scaleFactor, {
        x: event.clientX - rect.left,
        y: event.clientY - rect.top,
      });
    },
    [zoomTo]
  );

  if (error) {
    return <pre className={styles.error}>{error}</pre>;
  }

  if (!result) return null;

  return (
    <div
      ref={viewerRef}
      data-mermaid-viewer
      className={`${styles.viewer} ${isFullscreen ? styles.fullscreen : ""}`}
    >
      <div className={styles.header}>
        {exportError ? (
          <span className={styles.exportError} role="status">
            {exportError}
          </span>
        ) : null}
        <div className={styles.toolbar}>
          <button
            type="button"
            className={styles.control}
            title="Zoom out"
            aria-label="Zoom out"
            onClick={() => zoomTo(view.scale - SCALE_STEP)}
            disabled={view.scale <= MIN_SCALE}
          >
            <ZoomOut aria-hidden="true" />
          </button>
          <span className={styles.zoomValue}>{Math.round(view.scale * 100)}%</span>
          <button
            type="button"
            className={styles.control}
            title="Zoom in"
            aria-label="Zoom in"
            onClick={() => zoomTo(view.scale + SCALE_STEP)}
            disabled={view.scale >= MAX_SCALE}
          >
            <ZoomIn aria-hidden="true" />
          </button>
          <button
            type="button"
            className={styles.control}
            title="Fit to canvas"
            aria-label="Fit to canvas"
            onClick={fitToCanvas}
          >
            <Maximize aria-hidden="true" />
          </button>
          <button
            type="button"
            className={styles.control}
            title="Actual size"
            aria-label="Actual size"
            onClick={actualSize}
          >
            <RotateCcw aria-hidden="true" />
          </button>
          <button
            type="button"
            className={styles.control}
            title="Export SVG"
            aria-label="Export SVG"
            onClick={downloadSvg}
          >
            <Download aria-hidden="true" />
          </button>
          <button
            type="button"
            className={styles.control}
            title={isExportingPng ? "Exporting PNG" : "Export PNG"}
            aria-label={isExportingPng ? "Exporting PNG" : "Export PNG"}
            onClick={() => void downloadPng()}
            disabled={isExportingPng}
          >
            <FileImage aria-hidden="true" />
          </button>
          <button
            type="button"
            className={styles.control}
            title={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
            aria-label={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
            onClick={() => void toggleFullscreen()}
          >
            {isFullscreen ? (
              <Minimize2 aria-hidden="true" />
            ) : (
              <Maximize2 aria-hidden="true" />
            )}
          </button>
        </div>
      </div>
      <div
        ref={viewportRef}
        className={styles.viewport}
        data-dragging={isDragging ? "true" : undefined}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
        onWheel={handleWheel}
      >
        <div
          ref={diagramRef}
          className={styles.diagram}
          style={{
            transform: `matrix(${view.scale}, 0, 0, ${view.scale}, ${view.x}, ${view.y})`,
          }}
          dangerouslySetInnerHTML={{ __html: result.svg }}
        />
      </div>
    </div>
  );
};

async function exitFullscreen() {
  if (document.fullscreenElement && document.exitFullscreen) {
    await document.exitFullscreen();
  }
}

function readSvgSize(svg: SVGSVGElement): SvgSize {
  const viewBox = svg.viewBox.baseVal;
  if (viewBox.width > 0 && viewBox.height > 0) {
    return { width: viewBox.width, height: viewBox.height };
  }

  const width = parseSvgLength(svg.getAttribute("width"));
  const height = parseSvgLength(svg.getAttribute("height"));
  if (width && height) {
    return { width, height };
  }

  try {
    const box = svg.getBBox();
    if (box.width > 0 && box.height > 0) {
      return { width: box.width, height: box.height };
    }
  } catch {
    // Some browsers throw when the SVG is not fully laid out yet.
  }

  return { width: 900, height: 480 };
}

function centerView({
  viewport,
  size,
  scale,
}: {
  viewport: HTMLDivElement;
  size: SvgSize;
  scale: number;
}): ViewState {
  const scaledWidth = size.width * scale;
  const scaledHeight = size.height * scale;
  const centeredX = (viewport.clientWidth - scaledWidth) / 2;
  const centeredY = (viewport.clientHeight - scaledHeight) / 2;

  return {
    scale,
    x: scaledWidth <= viewport.clientWidth
      ? Math.max(VIEW_PADDING, centeredX)
      : VIEW_PADDING,
    y: scaledHeight <= viewport.clientHeight
      ? Math.max(VIEW_PADDING, centeredY)
      : VIEW_PADDING,
  };
}

function parseSvgLength(value: string | null): number | null {
  if (!value) return null;
  const match = value.match(/^([\d.]+)/);
  if (!match) return null;
  const parsed = Number.parseFloat(match[1]);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

function clampScale(value: number) {
  return Math.min(MAX_SCALE, Math.max(MIN_SCALE, value));
}

function roundScale(value: number) {
  return Math.round(value * 100) / 100;
}

function normalizeWheelDelta(
  event: WheelEvent<HTMLDivElement>,
  viewportHeight: number
) {
  if (event.deltaMode === 1) {
    return event.deltaY * 16;
  }

  if (event.deltaMode === 2) {
    return event.deltaY * viewportHeight;
  }

  return event.deltaY;
}

function hashString(value: string) {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash << 5) - hash + value.charCodeAt(index);
    hash |= 0;
  }
  return Math.abs(hash).toString(36);
}

function serializeSvgForExport(svg: SVGSVGElement, size: SvgSize) {
  const clone = svg.cloneNode(true) as SVGSVGElement;
  const width = Math.max(1, Math.ceil(size.width));
  const height = Math.max(1, Math.ceil(size.height));

  clone.setAttribute("xmlns", SVG_NS);
  clone.setAttribute("xmlns:xlink", XLINK_NS);
  clone.setAttribute("width", String(width));
  clone.setAttribute("height", String(height));
  clone.setAttribute(
    "viewBox",
    clone.getAttribute("viewBox") || `0 0 ${size.width} ${size.height}`
  );
  clone.setAttribute("preserveAspectRatio", "xMidYMid meet");
  clone.removeAttribute("style");

  clone.querySelectorAll("foreignObject *").forEach((element) => {
    if (!element.getAttribute("xmlns")) {
      element.setAttribute("xmlns", XHTML_NS);
    }
  });

  const markup = new XMLSerializer().serializeToString(clone);
  return `<?xml version="1.0" encoding="UTF-8"?>\n${markup}`;
}

function svgToDataUrl(markup: string) {
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(markup)}`;
}

function getExportScale(size: SvgSize) {
  const pixelScale = Math.sqrt(
    MAX_EXPORT_PIXELS / Math.max(1, size.width * size.height)
  );
  const dimensionScale = Math.min(
    MAX_EXPORT_DIMENSION / Math.max(1, size.width),
    MAX_EXPORT_DIMENSION / Math.max(1, size.height)
  );

  return Math.max(0.01, Math.min(EXPORT_PIXEL_RATIO, pixelScale, dimensionScale));
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}

function loadImage(src: string) {
  return new Promise<HTMLImageElement>((resolve, reject) => {
    const image = new Image();
    image.decoding = "sync";
    image.onload = () => resolve(image);
    image.onerror = () => {
      reject(new Error("The exported Mermaid SVG could not be rasterized."));
    };
    image.src = src;
  });
}

export default Mermaid;
