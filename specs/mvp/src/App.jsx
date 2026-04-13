import React, { Suspense, useEffect, useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  AppWindow,
  BookOpenText,
  Braces,
  Database,
  FileCode2,
  FileJson,
  FileText,
  Menu,
  Search,
  Sparkles,
  Workflow,
  X
} from 'lucide-react';
import MermaidDiagram from './components/MermaidDiagram';

// const PrototypeApp = React.lazy(() => import('@prototype'));
const OpenApiRenderer = React.lazy(() => import('./components/OpenApiRenderer'));
const DOCUMENT_LOADERS = import.meta.glob('../../cortex-*.{md,sql,yaml}', {
  query: '?raw',
  import: 'default'
});

const SPEC_CATALOG = [
  // {
  //   id: 'prototype',
  //   title: '交互原型',
  //   fileName: 'cortex-prototype.jsx',
  //   kind: 'prototype',
  //   group: '核心体验',
  //   icon: AppWindow,
  //   summary: '直接运行原型组件，查看工作台交互与页面布局。'
  // },
  {
    id: 'prd',
    title: '需求文档',
    fileName: 'cortex-prd.md',
    path: '../../cortex-prd.md',
    kind: 'markdown',
    group: '业务规格',
    icon: BookOpenText,
    summary: '产品愿景、功能模块与非功能需求。'
  },
  {
    id: 'dfd',
    title: '数据流样例',
    fileName: 'cortex-dfd.md',
    path: '../../cortex-dfd.md',
    kind: 'markdown',
    group: '业务规格',
    icon: Workflow,
    summary: '用于校验源、任务、执行与产出链路的数据流样例。'
  },
  {
    id: 'schema',
    title: 'Schema 设计',
    fileName: 'cortex-schema.md',
    path: '../../cortex-schema.md',
    kind: 'markdown',
    group: '系统设计',
    icon: Database,
    summary: '权威 Schema 设计、ER 关系与审查路径。'
  },
  {
    id: 'sql',
    title: '标准 SQL DDL',
    fileName: 'cortex-init.sql',
    path: '../../cortex-init.sql',
    kind: 'code',
    language: 'sql',
    group: '工程产物',
    icon: FileCode2,
    summary: '面向生产环境的标准 SQL DDL。'
  },
  {
    id: 'api',
    title: 'OpenAPI 文档',
    fileName: 'cortex-api.yaml',
    path: '../../cortex-api.yaml',
    kind: 'openapi',
    language: 'yaml',
    group: '工程产物',
    icon: FileJson,
    summary: '支持 Swagger UI、Swagger Editor 与源码视图的 OpenAPI 契约文档。'
  },
  {
    id: 'tech',
    title: '技术说明',
    fileName: 'cortex-tech.md',
    path: '../../cortex-tech.md',
    kind: 'markdown',
    group: '工程产物',
    icon: FileText,
    summary: '可用于补充术语表、字段字典与实现说明。'
  },
  {
    id: 'task',
    title: '任务计划',
    fileName: 'cortex-tasks.md',
    path: '../../cortex-tasks.md',
    kind: 'markdown',
    group: '工程产物',
    icon: FileText,
    summary: '用于规划和执行详细的开发计划。'
  },
  {
    id: 'log',
    title: '任务日志',
    fileName: 'cortex-log.md',
    path: '../../cortex-log.md',
    kind: 'markdown',
    group: '工程产物',
    icon: FileText,
    summary: '用于记录任务执行过程的日志、问题和解决方案。'
  }
];

const GROUP_ORDER = ['核心体验', '业务规格', '系统设计', '工程产物'];
const DEFAULT_ENTRY_ID = 'prototype';

function getEntryById(id) {
  return SPEC_CATALOG.find((entry) => entry.id === id) ?? SPEC_CATALOG[0];
}

function readHashId() {
  if (typeof window === 'undefined') {
    return DEFAULT_ENTRY_ID;
  }

  const hashValue = window.location.hash.replace(/^#/, '').trim();
  if (!hashValue) {
    return DEFAULT_ENTRY_ID;
  }

  return getEntryById(decodeURIComponent(hashValue)).id;
}

function formatSize(text) {
  const size = new Blob([text ?? '']).size;
  if (size < 1024) {
    return `${size} B`;
  }

  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }

  return `${(size / (1024 * 1024)).toFixed(2)} MB`;
}

function getLineCount(text) {
  if (!text) {
    return 0;
  }

  return text.split(/\r?\n/).length;
}

function getKindLabel(entry) {
  if (entry.kind === 'markdown') {
    return 'Markdown';
  }

  if (entry.kind === 'openapi') {
    return 'OpenAPI';
  }

  if (entry.kind === 'code') {
    return (entry.language ?? 'Text').toUpperCase();
  }

  return 'React';
}

function FullscreenLoading({ title, description }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top,_rgba(148,163,184,0.18),_transparent_38%),linear-gradient(180deg,#f8fafc_0%,#eef2f7_100%)] px-6 text-center">
      <div className="rounded-[28px] border border-slate-200 bg-white px-8 py-12 shadow-[0_18px_48px_rgba(15,23,42,0.08)]">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100 text-slate-500">
          <Sparkles className="h-6 w-6" />
        </div>
        <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
        <p className="mt-2 max-w-md text-sm leading-7 text-slate-600">{description}</p>
      </div>
    </div>
  );
}

function MarkdownRenderer({ content }) {
  if (!content.trim()) {
    return <EmptyState title="当前文档为空" description="这个文档还没有内容，后续补充后会直接在这里展示。" />;
  }

  return (
    <article className="doc-markdown rounded-[28px] border border-slate-200 bg-white p-8 shadow-[0_18px_48px_rgba(15,23,42,0.08)]">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code(props) {
            const { className, children, ...rest } = props;
            const value = String(children ?? '').replace(/\n$/, '');
            const isBlock = value.includes('\n');
            const languageMatch = /language-([\w-]+)/.exec(className ?? '');
            const language = languageMatch?.[1]?.toLowerCase();

            if (language === 'mermaid' && isBlock) {
              return <MermaidDiagram chart={value} />;
            }

            if (!isBlock) {
              return (
                <code className="rounded-md bg-slate-100 px-1.5 py-0.5 text-[0.92em] text-slate-700" {...rest}>
                  {children}
                </code>
              );
            }

            return (
              <pre className="overflow-x-auto rounded-2xl bg-slate-950 p-4 text-sm leading-7 text-slate-100">
                <code className={className} {...rest}>
                  {children}
                </code>
              </pre>
            );
          },
          a(props) {
            const { href, children, ...rest } = props;
            return (
              <a href={href} target="_blank" rel="noreferrer" {...rest}>
                {children}
              </a>
            );
          },
          table(props) {
            return (
              <div className="overflow-x-auto">
                <table {...props} />
              </div>
            );
          }
        }}
      >
        {content}
      </ReactMarkdown>
    </article>
  );
}

function CodeRenderer({ entry }) {
  if (!entry.content.trim()) {
    return <EmptyState title="当前文件为空" description="这个工程文件已纳入导航，但内容还没有写入。" />;
  }

  return (
    <section className="overflow-hidden rounded-[28px] border border-slate-800 bg-slate-950 shadow-[0_18px_48px_rgba(15,23,42,0.18)]">
      <div className="flex items-center justify-between border-b border-slate-800 px-5 py-3 text-xs text-slate-400">
        <div className="flex items-center gap-3">
          <span className="rounded-full border border-slate-700 px-2.5 py-1 uppercase tracking-[0.18em] text-slate-300">
            {entry.language ?? 'text'}
          </span>
          <span>{getLineCount(entry.content)} 行</span>
        </div>
        <span>{formatSize(entry.content)}</span>
      </div>
      <pre className="doc-code overflow-x-auto p-5 text-sm leading-6 text-slate-100">{entry.content}</pre>
    </section>
  );
}

function EmptyState({ title, description }) {
  return (
    <div className="rounded-[28px] border border-dashed border-slate-300 bg-white/80 px-8 py-16 text-center shadow-[0_18px_48px_rgba(15,23,42,0.05)]">
      <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100 text-slate-500">
        <Sparkles className="h-6 w-6" />
      </div>
      <h3 className="text-lg font-semibold text-slate-900">{title}</h3>
      <p className="mx-auto mt-2 max-w-xl text-sm leading-7 text-slate-600">{description}</p>
    </div>
  );
}

function LoadErrorState({ title, description }) {
  return (
    <div className="rounded-[28px] border border-rose-200 bg-rose-50 px-8 py-16 text-center shadow-[0_18px_48px_rgba(15,23,42,0.05)]">
      <h3 className="text-lg font-semibold text-rose-900">{title}</h3>
      <p className="mx-auto mt-2 max-w-xl text-sm leading-7 text-rose-700">{description}</p>
    </div>
  );
}

function SpecNav({ activeId, onSelect, searchQuery, onSearchChange, compact = false }) {
  const groupedEntries = useMemo(() => {
    const keyword = searchQuery.trim();

    return GROUP_ORDER.map((groupName) => {
      const entries = SPEC_CATALOG.filter((entry) => entry.group === groupName).filter((entry) => {
        if (!keyword) {
          return true;
        }

        return [entry.title, entry.fileName, entry.summary].some((field) => field.toLowerCase().includes(keyword.toLowerCase()));
      });

      return { groupName, entries };
    }).filter((group) => group.entries.length > 0);
  }, [searchQuery]);

  return (
    <div className={`flex h-full min-h-0 flex-col ${compact ? 'w-[22rem]' : 'w-full'}`}>
      <div className="border-b border-slate-200 px-5 py-5">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-900 text-white shadow-lg shadow-slate-900/15">
            <Braces className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-900">Specs Navigator</p>
            <p className="text-xs text-slate-500">在文档与原型之间快速切换</p>
          </div>
        </div>
        <label className="mt-4 flex items-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-500 focus-within:border-slate-400 focus-within:bg-white">
          <Search className="h-4 w-4" />
          <input
            value={searchQuery}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder="搜索文档或原型"
            className="w-full bg-transparent outline-none placeholder:text-slate-400"
          />
        </label>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-3 py-4">
        <div className="space-y-5">
          {groupedEntries.map((group) => (
            <section key={group.groupName}>
              <div className="mb-2 px-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
                {group.groupName}
              </div>
              <div className="space-y-1.5">
                {group.entries.map((entry) => {
                  const Icon = entry.icon;
                  const isActive = entry.id === activeId;

                  return (
                    <button
                      key={entry.id}
                      type="button"
                      onClick={() => onSelect(entry.id)}
                      className={`w-full rounded-2xl border px-3 py-3 text-left transition ${
                        isActive
                          ? 'border-slate-900 bg-slate-900 text-white shadow-lg shadow-slate-900/20'
                          : 'border-transparent bg-white text-slate-700 hover:border-slate-200 hover:bg-slate-50'
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <div
                          className={`mt-0.5 flex h-9 w-9 items-center justify-center rounded-xl ${
                            isActive ? 'bg-white/12 text-white' : 'bg-slate-100 text-slate-600'
                          }`}
                        >
                          <Icon className="h-4.5 w-4.5" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center justify-between gap-3">
                            <p className={`truncate text-sm font-semibold ${isActive ? 'text-white' : 'text-slate-900'}`}>
                              {entry.title}
                            </p>
                            <span
                              className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em] ${
                                isActive ? 'bg-white/12 text-slate-200' : 'bg-slate-100 text-slate-500'
                              }`}
                            >
                              {entry.kind === 'markdown'
                                ? 'md'
                                : entry.kind === 'openapi'
                                  ? 'api'
                                  : entry.kind === 'code'
                                    ? entry.language
                                    : 'ui'}
                            </span>
                          </div>
                          <p className={`mt-1 line-clamp-2 text-xs leading-5 ${isActive ? 'text-slate-300' : 'text-slate-500'}`}>
                            {entry.summary}
                          </p>
                          <p className="mt-2 truncate text-[11px] text-slate-400">{entry.fileName}</p>
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}

function DocumentView({
  entry,
  markdownMode,
  onMarkdownModeChange,
  openApiMode,
  onOpenApiModeChange,
  isLoading,
  errorMessage
}) {
  const lineCount = getLineCount(entry.content);

  return (
    <div className="min-w-0 flex-1 overflow-y-auto">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-6 py-6 lg:px-10 lg:py-8">
        <section className="rounded-[30px] border border-slate-200 bg-white/88 p-6 shadow-[0_18px_48px_rgba(15,23,42,0.06)] backdrop-blur">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
            <div className="min-w-0">
              <div className="mb-3 inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-slate-600">
                {entry.group}
              </div>
              <h1 className="text-3xl font-semibold tracking-tight text-slate-950">{entry.title}</h1>
              <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-600">{entry.summary}</p>
            </div>

            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:min-w-[26rem]">
              <MetaCard label="文件" value={entry.fileName} />
              <MetaCard label="类型" value={getKindLabel(entry)} />
              <MetaCard label="大小" value={isLoading ? '加载中' : formatSize(entry.content)} />
              <MetaCard label="行数" value={isLoading ? '--' : `${lineCount}`} />
            </div>
          </div>

          {entry.kind === 'markdown' && (
            <div className="mt-5 flex items-center gap-2">
              <ModeButton active={markdownMode === 'rendered'} onClick={() => onMarkdownModeChange('rendered')}>
                渲染视图
              </ModeButton>
              <ModeButton active={markdownMode === 'raw'} onClick={() => onMarkdownModeChange('raw')}>
                源码视图
              </ModeButton>
            </div>
          )}

          {entry.kind === 'openapi' && (
            <div className="mt-5 flex flex-wrap items-center gap-2">
              <ModeButton active={openApiMode === 'swagger'} onClick={() => onOpenApiModeChange('swagger')}>
                Swagger UI
              </ModeButton>
              <ModeButton active={openApiMode === 'editor'} onClick={() => onOpenApiModeChange('editor')}>
                Swagger Editor
              </ModeButton>
              <ModeButton active={openApiMode === 'raw'} onClick={() => onOpenApiModeChange('raw')}>
                源码视图
              </ModeButton>
            </div>
          )}
        </section>

        {errorMessage ? <LoadErrorState title="文档加载失败" description={errorMessage} /> : null}
        {isLoading ? <FullscreenLoading title="正在加载文档" description={`正在读取 ${entry.fileName}，稍后会自动展示内容。`} /> : null}
        {!isLoading && !errorMessage && entry.kind === 'markdown' && markdownMode === 'rendered' ? <MarkdownRenderer content={entry.content} /> : null}
        {!isLoading && !errorMessage && entry.kind === 'markdown' && markdownMode === 'raw' ? (
          <CodeRenderer entry={{ ...entry, language: 'markdown' }} />
        ) : null}
        {!isLoading && !errorMessage && entry.kind === 'openapi' && openApiMode === 'raw' ? (
          <CodeRenderer entry={{ ...entry, language: 'yaml' }} />
        ) : null}
        {!isLoading && !errorMessage && entry.kind === 'openapi' && openApiMode !== 'raw' ? (
          <Suspense fallback={<FullscreenLoading title="正在渲染 OpenAPI" description="正在加载 Swagger 渲染器与编辑器资源。" />}>
            <OpenApiRenderer content={entry.content} mode={openApiMode} />
          </Suspense>
        ) : null}
        {!isLoading && !errorMessage && entry.kind === 'code' ? <CodeRenderer entry={entry} /> : null}
      </div>
    </div>
  );
}

function MetaCard({ label, value }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
      <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">{label}</div>
      <div className="mt-2 truncate text-sm font-medium text-slate-800">{value}</div>
    </div>
  );
}

function ModeButton({ active, onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full px-4 py-2 text-sm font-medium transition ${
        active ? 'bg-slate-900 text-white shadow-lg shadow-slate-900/15' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
      }`}
    >
      {children}
    </button>
  );
}

function DocsWorkspace({
  activeEntry,
  activeId,
  onSelect,
  searchQuery,
  onSearchChange,
  markdownMode,
  onMarkdownModeChange,
  openApiMode,
  onOpenApiModeChange,
  isLoading,
  errorMessage
}) {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <div className="flex min-h-screen bg-[radial-gradient(circle_at_top,_rgba(148,163,184,0.18),_transparent_38%),linear-gradient(180deg,#f8fafc_0%,#eef2f7_100%)] text-slate-900">
      <aside
        className={`border-r border-slate-200 bg-white/82 backdrop-blur transition-all duration-300 ${
          sidebarOpen ? 'w-[22rem]' : 'w-0 overflow-hidden border-r-0'
        }`}
      >
        <SpecNav activeId={activeId} onSelect={onSelect} searchQuery={searchQuery} onSearchChange={onSearchChange} />
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex items-center justify-between border-b border-slate-200 bg-white/78 px-4 py-3 backdrop-blur lg:px-6">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setSidebarOpen((value) => !value)}
              className="inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-slate-200 bg-white text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
            >
              <Menu className="h-4.5 w-4.5" />
            </button>
            <div>
              <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">cortex Specs</div>
              <div className="text-sm font-medium text-slate-700">文档浏览模式</div>
            </div>
          </div>

          <div className="hidden items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-2 text-xs text-slate-500 shadow-sm md:flex">
            <span className="inline-flex h-2 w-2 rounded-full bg-emerald-500" />
            当前文档：{activeEntry.fileName}
          </div>
        </header>

        <DocumentView
          entry={activeEntry}
          markdownMode={markdownMode}
          onMarkdownModeChange={onMarkdownModeChange}
          openApiMode={openApiMode}
          onOpenApiModeChange={onOpenApiModeChange}
          isLoading={isLoading}
          errorMessage={errorMessage}
        />
      </div>
    </div>
  );
}

function PrototypeWorkspace({ activeId, onSelect, searchQuery, onSearchChange }) {
  const [navOpen, setNavOpen] = useState(false);

  return (
    <div className="relative min-h-screen bg-slate-950">
      <div className="fixed left-4 top-4 z-[120] flex items-center gap-3">
        <button
          type="button"
          onClick={() => setNavOpen((value) => !value)}
          className="inline-flex items-center gap-2 rounded-2xl border border-white/15 bg-slate-950/88 px-4 py-3 text-sm font-medium text-white shadow-2xl shadow-slate-950/30 backdrop-blur transition hover:bg-slate-900"
        >
          {navOpen ? <X className="h-4.5 w-4.5" /> : <Menu className="h-4.5 w-4.5" />}
          浏览 Specs
        </button>
        <div className="hidden rounded-full border border-white/15 bg-slate-950/70 px-3 py-2 text-xs text-slate-200 backdrop-blur md:flex">
          原型沉浸视图
        </div>
      </div>

      {navOpen && (
        <div className="fixed inset-0 z-[110] bg-slate-950/35 backdrop-blur-[2px]" onClick={() => setNavOpen(false)}>
          <div className="absolute left-4 top-20 h-[calc(100vh-6rem)] rounded-[28px] border border-slate-200 bg-white shadow-[0_28px_80px_rgba(15,23,42,0.24)]" onClick={(event) => event.stopPropagation()}>
            <SpecNav
              activeId={activeId}
              onSelect={(nextId) => {
                onSelect(nextId);
                setNavOpen(false);
              }}
              searchQuery={searchQuery}
              onSearchChange={onSearchChange}
              compact
            />
          </div>
        </div>
      )}

      <Suspense fallback={<FullscreenLoading title="正在加载原型" description="原型文件较大，首次进入会稍等片刻。" />}>
        <PrototypeApp />
      </Suspense>
    </div>
  );
}

export default function App() {
  const [activeId, setActiveId] = useState(readHashId);
  const [searchQuery, setSearchQuery] = useState('');
  const [markdownMode, setMarkdownMode] = useState('rendered');
  const [openApiMode, setOpenApiMode] = useState('swagger');
  const [contentCache, setContentCache] = useState({});
  const [loadingId, setLoadingId] = useState(null);
  const [loadErrors, setLoadErrors] = useState({});

  const activeEntryBase = useMemo(() => getEntryById(activeId), [activeId]);
  const activeContent = activeEntryBase.path ? contentCache[activeEntryBase.path] ?? '' : '';
  const activeEntry = useMemo(() => ({ ...activeEntryBase, content: activeContent }), [activeEntryBase, activeContent]);

  useEffect(() => {
    const nextHash = `#${activeId}`;
    if (window.location.hash !== nextHash) {
      window.history.replaceState(null, '', nextHash);
    }
  }, [activeId]);

  useEffect(() => {
    const handleHashChange = () => setActiveId(readHashId());
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  useEffect(() => {
    if (activeEntry.kind === 'markdown') {
      setMarkdownMode('rendered');
    }

    if (activeEntry.kind === 'openapi') {
      setOpenApiMode('swagger');
    }
  }, [activeEntry.id, activeEntry.kind]);

  useEffect(() => {
    if (!activeEntry.path || contentCache[activeEntry.path] !== undefined) {
      return;
    }

    const loader = DOCUMENT_LOADERS[activeEntry.path];
    if (!loader) {
      setLoadErrors((current) => ({
        ...current,
        [activeEntry.id]: `未找到 ${activeEntry.fileName} 的加载器，请检查目录结构是否仍在 specs 根目录。`
      }));
      return;
    }

    let disposed = false;
    setLoadingId(activeEntry.id);

    loader()
      .then((content) => {
        if (disposed) {
          return;
        }

        setContentCache((current) => ({
          ...current,
          [activeEntry.path]: typeof content === 'string' ? content : ''
        }));
        setLoadErrors((current) => {
          const next = { ...current };
          delete next[activeEntry.id];
          return next;
        });
      })
      .catch((error) => {
        if (disposed) {
          return;
        }

        setLoadErrors((current) => ({
          ...current,
          [activeEntry.id]: `读取 ${activeEntry.fileName} 失败：${error instanceof Error ? error.message : String(error)}`
        }));
      })
      .finally(() => {
        if (!disposed) {
          setLoadingId((current) => (current === activeEntry.id ? null : current));
        }
      });

    return () => {
      disposed = true;
    };
  }, [activeEntry.fileName, activeEntry.id, activeEntry.path, contentCache]);

  if (activeEntry.kind === 'prototype') {
    return (
      <PrototypeWorkspace
        activeId={activeId}
        onSelect={setActiveId}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
      />
    );
  }

  return (
    <DocsWorkspace
      activeEntry={activeEntry}
      activeId={activeId}
      onSelect={setActiveId}
      searchQuery={searchQuery}
      onSearchChange={setSearchQuery}
      markdownMode={markdownMode}
      onMarkdownModeChange={setMarkdownMode}
      openApiMode={openApiMode}
      onOpenApiModeChange={setOpenApiMode}
      isLoading={loadingId === activeEntry.id && activeEntry.content === ''}
      errorMessage={loadErrors[activeEntry.id] ?? ''}
    />
  );
}
