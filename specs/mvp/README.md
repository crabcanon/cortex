# Ordix Prototype MVP

这个子目录是 `specs` 下的最小可运行 React MVP 环境，用来直接挂载上层的 `ordix-prototype.jsx`，同时提供一个可在浏览器中切换查看原型与规格文档的浏览壳层。

## 目录约定

- `../ordix-prototype.jsx`：权威原型文件，MVP 直接引用，不做复制。
- `src/main.jsx`：运行入口。
- `src/App.jsx`：Specs 浏览器壳层，负责原型与文档切换。
- `src/styles.css`：最小 Tailwind 样式层和文档阅读样式。

## 运行方式

```bash
cd D:\code\codex\ordix\specs\mvp
npm install
npm run dev
```

默认开发地址通常是 `http://localhost:5173`。

## 浏览说明

- 默认进入 `交互原型` 视图。
- 原型页左上角有 `浏览 Specs` 按钮，可切换到 `PRD / DFD / Schema / SQL / API / Tech`。
- 文档页左侧是导航栏，支持搜索和切换文档。
- Markdown 文档支持 `渲染视图 / 源码视图` 两种阅读方式。
- SQL / YAML 等工程文件使用代码视图展示。

## 维护建议

- 如果你更新了 `specs/ordix-prototype.jsx`，这里不需要额外同步，刷新即可生效。
- 如果你更新了 `specs` 根目录下的文档文件，这里的文档浏览器也会自动读取最新内容。
- 如果后续需要把原型逐步演进成正式前端，建议继续保持 `specs/mvp` 只做原型运行壳层，不在这里堆业务实现。
