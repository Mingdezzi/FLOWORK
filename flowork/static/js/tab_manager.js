class TabManager {
    constructor() {
        this.tabBar = document.getElementById('tab-bar');
        this.tabContent = document.getElementById('tab-content');
        this.sidebarLinks = document.querySelectorAll('.sidebar-area a, .mobile-top-header a');
        this.isFrame = window.self !== window.top;
        this.dragSrcEl = null;

        this.init();
    }

    init() {
        if (this.isFrame) {
            document.body.classList.add('iframe-mode');
            this.setupIframeCommunication();
        } else {
            this.setupShell();
        }
    }

    setupShell() {
        const initialTabId = 'tab-' + Date.now();
        const initialPane = this.tabContent.querySelector('.tab-pane');
        if (initialPane) {
            initialPane.id = initialTabId;
            const pageTitle = document.title.split('-')[0].trim() || '홈';
            this.createTabButton(initialTabId, pageTitle, true, false);
        }

        this.sidebarLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                const href = link.getAttribute('href');
                if (href && href !== '#' && !href.startsWith('javascript')) {
                    e.preventDefault();
                    const title = link.textContent.trim() || '메뉴';
                    this.openTab(title, href);
                    
                    if (window.innerWidth < 992) {
                        const offcanvasEl = document.getElementById('mobileMenuSidebar');
                        if (offcanvasEl) {
                            const bsOffcanvas = bootstrap.Offcanvas.getInstance(offcanvasEl);
                            if (bsOffcanvas) bsOffcanvas.hide();
                        }
                    }
                }
            });
        });

        this.setupDragAndDrop();
    }

    setupIframeCommunication() {
        document.addEventListener('click', (e) => {
            const link = e.target.closest('a');
            if (link) {
                const href = link.getAttribute('href');
                if (href && !href.startsWith('#') && !href.startsWith('javascript')) {
                    
                }
            }
        });
    }

    openTab(title, url) {
        const existingTab = Array.from(this.tabBar.children).find(tab => tab.dataset.url === url);
        
        if (existingTab) {
            this.activateTab(existingTab.id);
            return;
        }

        const tabId = 'tab-' + Date.now();
        this.createTabButton(tabId, title, true, true, url);
        this.createIframe(tabId, url);
    }

    createTabButton(id, title, isActive, isClosable, url = null) {
        const tab = document.createElement('div');
        tab.className = `tab-item ${isActive ? 'active' : ''}`;
        tab.id = id + '-btn';
        tab.dataset.target = id;
        tab.draggable = true; 
        if (url) tab.dataset.url = url;

        let html = `<span class="tab-title">${title}</span>`;
        if (isClosable) {
            html += `<span class="btn-close-tab"><i class="bi bi-x"></i></span>`;
        }
        tab.innerHTML = html;

        tab.addEventListener('click', (e) => {
            if (!e.target.closest('.btn-close-tab')) {
                this.activateTab(id);
            }
        });

        if (isClosable) {
            tab.querySelector('.btn-close-tab').addEventListener('click', (e) => {
                e.stopPropagation();
                this.closeTab(id);
            });
        }

        this.addDragEvents(tab);

        if (isActive) {
            const currentActive = this.tabBar.querySelector('.active');
            if (currentActive) currentActive.classList.remove('active');
        }

        this.tabBar.appendChild(tab);
        this.scrollToTab(tab);
    }

    createIframe(id, url) {
        const pane = document.createElement('div');
        pane.className = 'tab-pane active';
        pane.id = id;

        const iframe = document.createElement('iframe');
        const separator = url.includes('?') ? '&' : '?';
        iframe.src = url + separator + 'iframe=1';
        iframe.className = 'tab-frame';
        iframe.frameBorder = '0';
        
        iframe.onload = () => {
            try {
                const iframeWin = iframe.contentWindow;
                iframeWin.alert = window.alert;
                iframeWin.confirm = window.confirm;
                iframeWin.prompt = window.prompt;
            } catch (e) {
                console.log('Cross-origin iframe detected or error accessing content');
            }
        };

        pane.appendChild(iframe);
        
        const currentActive = this.tabContent.querySelector('.tab-pane.active');
        if (currentActive && currentActive.id !== id) {
            currentActive.classList.remove('active');
        }

        this.tabContent.appendChild(pane);
    }

    activateTab(id) {
        const tabs = this.tabBar.querySelectorAll('.tab-item');
        const panes = this.tabContent.querySelectorAll('.tab-pane');

        tabs.forEach(t => {
            if (t.dataset.target === id) t.classList.add('active');
            else t.classList.remove('active');
        });

        panes.forEach(p => {
            if (p.id === id) p.classList.add('active');
            else p.classList.remove('active');
        });
    }

    closeTab(id) {
        const tabBtn = document.getElementById(id + '-btn');
        const tabPane = document.getElementById(id);

        if (tabBtn.classList.contains('active')) {
            const sibling = tabBtn.previousElementSibling || tabBtn.nextElementSibling;
            if (sibling) {
                this.activateTab(sibling.dataset.target);
            }
        }

        tabBtn.remove();
        tabPane.remove();
    }

    scrollToTab(tab) {
        this.tabBar.scrollLeft = tab.offsetLeft - this.tabBar.offsetLeft;
    }

    setupDragAndDrop() {
        this.tabBar.addEventListener('dragover', (e) => {
            e.preventDefault();
            return false;
        });
    }

    addDragEvents(item) {
        item.addEventListener('dragstart', (e) => {
            this.dragSrcEl = item;
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/html', item.outerHTML);
            item.classList.add('dragging');
        });

        item.addEventListener('dragend', (e) => {
            item.classList.remove('dragging');
            this.tabBar.querySelectorAll('.tab-item').forEach(tab => {
                tab.classList.remove('over');
            });
        });

        item.addEventListener('dragenter', (e) => {
            if (this.dragSrcEl !== item) {
                item.classList.add('over');
            }
        });

        item.addEventListener('dragleave', (e) => {
            item.classList.remove('over');
        });

        item.addEventListener('drop', (e) => {
            e.stopPropagation();
            e.preventDefault();

            if (this.dragSrcEl !== item) {
                const nodes = Array.from(this.tabBar.children);
                const srcIndex = nodes.indexOf(this.dragSrcEl);
                const targetIndex = nodes.indexOf(item);

                if (srcIndex < targetIndex) {
                    item.after(this.dragSrcEl);
                } else {
                    item.before(this.dragSrcEl);
                }
            }
            return false;
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.tabManager = new TabManager();
});