// Intentionally no analytics, storage or vendor imports on a narrow device.
const desktop = matchMedia('(min-width: 1024px)');
if (desktop.matches) {
  try {
    const {startWorkspace} = await import('./deepblm-workspace.mjs');
    // A resize while modules load must not initialize the editor on a narrow screen.
    if (desktop.matches) await startWorkspace();
  } catch {
    document.querySelector('#entry-status').textContent = '工作台未能加载，请刷新重试；也可通过下方链接咨询。';
  }
}
// A desktop session survives resizing. A page first opened on a phone stays lightweight until reload.
