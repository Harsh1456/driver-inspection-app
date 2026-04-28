// Dashboard JavaScript functionality - Redesigned for Vanilla CSS
class Dashboard {
    constructor() {
        this.currentPage = 1;
        this.perPage = 10;
        this.searchTerm = '';
        this.searchDate = '';
        this.files = [];
        this.totalFiles = 0;
        
        this.init();
    }
    
    init() {
        this.loadStats();
        this.loadFiles();
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.addEventListener('input', this.debounce(() => {
                this.searchTerm = searchInput.value;
                this.currentPage = 1;
                this.loadFiles();
            }, 300));
        }
        
        const dateFilter = document.getElementById('date-filter');
        if (dateFilter) {
            dateFilter.addEventListener('change', () => {
                this.searchDate = dateFilter.value;
                this.currentPage = 1;
                this.loadFiles();
            });
        }
        
        document.getElementById('pagination-controls').addEventListener('click', (e) => {
            const btn = e.target.closest('.page-btn');
            if (btn) {
                this.currentPage = parseInt(btn.dataset.page);
                this.loadFiles();
            }
        });
    }
    
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    async loadStats() {
        try {
            const response = await fetch('/api/stats');
            const data = await response.json();
            if (data.success) {
                this.updateStatsDisplay(data.stats);
            }
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    }
    
    updateStatsDisplay(stats) {
        document.getElementById('total-files').textContent = stats.total_files.toLocaleString();
        document.getElementById('total-pages').textContent = stats.total_pages.toLocaleString();
        document.getElementById('pages-remarks').textContent = stats.pages_with_remarks.toLocaleString();
    }

    async loadFiles() {
        this.showLoading();
        try {
            const params = new URLSearchParams({
                page: this.currentPage,
                per_page: this.perPage,
                search: this.searchTerm
            });
            if (this.searchDate) params.append('date', this.searchDate);
            
            const response = await fetch(`/api/files?${params}`);
            const data = await response.json();
            
            if (data.success) {
                this.files = data.files;
                this.totalFiles = data.total;
                this.renderFiles();
                this.renderPagination();
                this.hideLoading();
            }
        } catch (error) {
            console.error('Error loading files:', error);
            this.hideLoading();
            this.showError('Failed to synchronize with server');
        }
    }
    
    renderFiles() {
        const tbody = document.getElementById('files-tbody');
        if (this.files.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6">
                        <div class="empty-state">
                            <div class="empty-state-icon">
                                <i class="fas fa-folder-open"></i>
                            </div>
                            <p style="font-weight: 700; font-size: var(--text-base); margin-bottom: 0.5rem; color: var(--text-600);">No reports found</p>
                            <p style="font-size: var(--text-sm); color: var(--text-faint); margin-bottom: 1.25rem;">Upload an inspection report to get started.</p>
                            <a href="/upload" class="btn btn-primary btn-sm">
                                <i class="fas fa-cloud-arrow-up"></i>
                                Upload Report
                            </a>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }
        
        tbody.innerHTML = this.files.map(file => this.renderFileRow(file)).join('');
        
        const startIndex = (this.currentPage - 1) * this.perPage + 1;
        const endIndex = Math.min(this.currentPage * this.perPage, this.totalFiles);
        document.getElementById('files-count').textContent = 
            `Showing ${startIndex} - ${endIndex} of ${this.totalFiles} repositories`;
    }
    
    renderFileRow(file) {
        const uploadDate = new Date(file.upload_timestamp).toLocaleDateString('en-US', {
            month: 'short', day: 'numeric', year: 'numeric'
        });
        const criticalityBadge = this.getCriticalityBadge(file.criticality_level);
        const remarksPct = file.total_pages > 0
            ? Math.round((file.pages_with_remarks / file.total_pages) * 100)
            : 0;

        return `
            <tr>
                <td>
                    <a href="/file/${file.file_id}" class="file-link">
                        ${this.escapeHtml(file.file_name)}
                    </a>
                </td>
                <td>
                    <span class="badge badge-gray" style="font-size:0.6rem;">${file.file_type.toUpperCase()}</span>
                </td>
                <td style="color:var(--text-faint); font-weight:600; white-space:nowrap;">${uploadDate}</td>
                <td>
                    <div style="display:flex; align-items:center; gap:0.5rem;">
                        <span style="font-weight:800; font-family:'Sora',sans-serif;">${file.total_pages}</span>
                        <span style="font-size:var(--text-xs); color:var(--text-faint); font-weight:600;">pages</span>
                    </div>
                </td>
                <td>${criticalityBadge}</td>
                <td style="text-align:right;">
                    <div style="display:flex; justify-content:flex-end; gap:0.5rem;">
                        <a href="/file/${file.file_id}" class="btn btn-secondary btn-sm" title="View report">
                            <i class="fas fa-eye"></i>
                        </a>
                        <button onclick="dashboard.deleteFile('${file.file_id}')" class="btn btn-danger btn-sm" title="Delete report">
                            <i class="fas fa-trash-alt"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }
    
    getCriticalityBadge(level) {
        switch(level) {
            case 'RED':    return '<span class="badge badge-red"><i class="fas fa-circle" style="font-size:.4rem;"></i> Critical</span>';
            case 'ORANGE': return '<span class="badge badge-orange"><i class="fas fa-circle" style="font-size:.4rem;"></i> Warning</span>';
            case 'GREEN':  return '<span class="badge badge-green"><i class="fas fa-circle" style="font-size:.4rem;"></i> Standard</span>';
            default:       return `<span class="badge badge-gray">${level}</span>`;
        }
    }
    
    renderPagination() {
        const totalPages = Math.ceil(this.totalFiles / this.perPage);
        const container = document.getElementById('pagination-controls');
        if (totalPages <= 1) {
            container.innerHTML = '';
            return;
        }
        
        let html = '';
        html += `
            <button class="btn btn-secondary page-btn" style="padding: 0.5rem 0.75rem;" ${this.currentPage === 1 ? 'disabled' : ''} data-page="${this.currentPage - 1}">
                <i class="fas fa-chevron-left" style="font-size: 0.75rem;"></i>
            </button>
        `;
        
        for (let i = 1; i <= totalPages; i++) {
            if (i === 1 || i === totalPages || (i >= this.currentPage - 1 && i <= this.currentPage + 1)) {
                html += `
                    <button class="btn ${i === this.currentPage ? 'btn-primary' : 'btn-secondary'} page-btn" style="min-width: 32px; padding: 0.5rem;" data-page="${i}">
                        ${i}
                    </button>
                `;
            } else if (i === this.currentPage - 2 || i === this.currentPage + 2) {
                html += `<span style="color: var(--text-muted); align-self: center;">...</span>`;
            }
        }
        
        html += `
            <button class="btn btn-secondary page-btn" style="padding: 0.5rem 0.75rem;" ${this.currentPage === totalPages ? 'disabled' : ''} data-page="${this.currentPage + 1}">
                <i class="fas fa-chevron-right" style="font-size: 0.75rem;"></i>
            </button>
        `;
        container.innerHTML = html;
    }
    
    async deleteFile(fileId) {
        if (!confirm('Permanent deletion cannot be undone. Proceed?')) return;
        try {
            const response = await fetch(`/api/file/${fileId}/delete`, { method: 'DELETE' });
            const data = await response.json();
            if (data.success) {
                this.showNotification('Data purged successfully', 'success');
                this.loadFiles();
                this.loadStats();
            }
        } catch (error) {
            this.showNotification('Purge operation failed', 'error');
        }
    }
    
    showLoading() {
        const spinner = document.getElementById('loading-spinner');
        if (spinner) spinner.style.display = 'flex';
        const tbody = document.getElementById('files-tbody');
        if (tbody) tbody.style.opacity = '0.4';
    }

    hideLoading() {
        const spinner = document.getElementById('loading-spinner');
        if (spinner) spinner.style.display = 'none';
        const tbody = document.getElementById('files-tbody');
        if (tbody) tbody.style.opacity = '1';
    }
    
    showError(message) {
        const tbody = document.getElementById('files-tbody');
        tbody.innerHTML = `
            <tr>
                <td colspan="6" style="padding: 4rem; text-align: center; color: var(--danger);">
                    <i class="fas fa-circle-exclamation" style="font-size: 2rem; margin-bottom: 1rem;"></i>
                    <p style="font-weight: 700;">${message}</p>
                    <button onclick="dashboard.loadFiles()" class="btn btn-ghost" style="margin-top: 1rem;">Retry Connection</button>
                </td>
            </tr>
        `;
    }
    
    showNotification(message, type) {
        const icons = { success:'fa-check-circle', error:'fa-circle-exclamation', info:'fa-info-circle' };
        const el = document.createElement('div');
        el.className = `toast ${type}`;
        el.innerHTML = `<i class="fas ${icons[type] || icons.info}" style="flex-shrink:0;"></i><span>${message}</span>`;

        let container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container';
            document.body.appendChild(container);
        }
        container.appendChild(el);

        setTimeout(() => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(8px)';
            el.style.transition = 'all 0.3s ease';
            setTimeout(() => el.remove(), 300);
        }, 3200);
    }
    
    escapeHtml(unsafe) {
        return unsafe.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
    }
}

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('files-tbody')) window.dashboard = new Dashboard();
});
