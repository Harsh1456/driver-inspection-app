// Dashboard JavaScript functionality

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
        // Search functionality
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.addEventListener('input', this.debounce(() => {
                this.searchTerm = searchInput.value;
                this.currentPage = 1;
                this.loadFiles();
            }, 300));
        }
        
        // Date filter functionality
        const dateFilter = document.getElementById('date-filter');
        if (dateFilter) {
            dateFilter.addEventListener('change', () => {
                this.searchDate = dateFilter.value;
                this.currentPage = 1;
                this.loadFiles();
            });
        }
        
        // Pagination event delegation
        document.getElementById('pagination-controls').addEventListener('click', (e) => {
            if (e.target.classList.contains('page-btn')) {
                this.currentPage = parseInt(e.target.dataset.page);
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
                search: this.searchTerm,
                date: this.searchDate
            });
            
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
            this.showError('Failed to load files');
        }
    }
    
    renderFiles() {
        const tbody = document.getElementById('files-tbody');
        
        if (this.files.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="py-8 text-center text-gray-500">
                        <i class="fas fa-inbox text-3xl mb-2"></i>
                        <p>No files found</p>
                    </td>
                </tr>
            `;
            return;
        }
        
        tbody.innerHTML = this.files.map(file => this.renderFileRow(file)).join('');
        
        // Update files count
        const startIndex = (this.currentPage - 1) * this.perPage + 1;
        const endIndex = Math.min(this.currentPage * this.perPage, this.totalFiles);
        document.getElementById('files-count').textContent = 
            `Showing ${startIndex}-${endIndex} of ${this.totalFiles} files`;
    }
    
    renderFileRow(file) {
        const uploadDate = new Date(file.upload_timestamp).toLocaleDateString();
        const criticalityClass = this.getCriticalityClass(file.criticality_level);
        
        return `
            <tr class="border-b border-gray-200 hover:bg-gray-50">
                <td class="py-4 px-6">
                    <a href="/file/${file.file_id}" class="font-medium text-gray-800 hover:text-green-600">
                        ${this.escapeHtml(file.file_name)}
                    </a>
                </td>
                <td class="py-4 px-6">
                    <span class="bg-gray-100 text-gray-700 px-2 py-1 rounded text-xs uppercase">
                        ${file.file_type}
                    </span>
                </td>
                <td class="py-4 px-6 text-gray-600">${uploadDate}</td>
                <td class="py-4 px-6 font-medium">${file.total_pages}</td>
                <td class="py-4 px-6">
                    <span class="font-medium ${file.pages_with_remarks > 0 ? 'text-orange-600' : 'text-green-600'}">
                        ${file.pages_with_remarks}
                    </span>
                </td>
                <td class="py-4 px-6">
                    <span class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${criticalityClass}">
                        ${file.criticality_level}
                    </span>
                </td>
                <td class="py-4 px-6 text-right">
                    <div class="flex justify-end space-x-2">
                        <a href="/file/${file.file_id}" 
                           class="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-gray-600 hover:bg-green-600 hover:text-white transition"
                           title="View Details">
                            <i class="fas fa-eye text-sm"></i>
                        </a>
                        <button onclick="dashboard.deleteFile('${file.file_id}')"
                                class="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-red-500 hover:bg-red-100 transition"
                                title="Delete File">
                            <i class="fas fa-trash text-sm"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }
    
    getCriticalityClass(level) {
        switch(level) {
            case 'RED': return 'bg-red-100 text-red-800';
            case 'ORANGE': return 'bg-orange-100 text-orange-800';
            case 'GREEN': return 'bg-green-100 text-green-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    }
    
    renderPagination() {
        const totalPages = Math.ceil(this.totalFiles / this.perPage);
        const paginationContainer = document.getElementById('pagination-controls');
        
        if (totalPages <= 1) {
            paginationContainer.innerHTML = '';
            return;
        }
        
        let paginationHTML = '';
        
        // Previous button
        paginationHTML += `
            <button class="w-8 h-8 rounded-full border border-gray-300 flex items-center justify-center text-gray-600 hover:bg-gray-100 page-btn ${this.currentPage === 1 ? 'opacity-50 cursor-not-allowed' : ''}"
                    ${this.currentPage === 1 ? 'disabled' : ''}
                    data-page="${this.currentPage - 1}">
                <i class="fas fa-chevron-left text-xs"></i>
            </button>
        `;
        
        // Page numbers
        for (let i = 1; i <= totalPages; i++) {
            if (i === 1 || i === totalPages || (i >= this.currentPage - 1 && i <= this.currentPage + 1)) {
                paginationHTML += `
                    <button class="w-8 h-8 rounded-full border border-gray-300 flex items-center justify-center page-btn ${i === this.currentPage ? 'bg-green-600 text-white border-green-600' : 'text-gray-600 hover:bg-gray-100'}"
                            data-page="${i}">
                        ${i}
                    </button>
                `;
            } else if (i === this.currentPage - 2 || i === this.currentPage + 2) {
                paginationHTML += `<span class="px-2 text-gray-500">...</span>`;
            }
        }
        
        // Next button
        paginationHTML += `
            <button class="w-8 h-8 rounded-full border border-gray-300 flex items-center justify-center text-gray-600 hover:bg-gray-100 page-btn ${this.currentPage === totalPages ? 'opacity-50 cursor-not-allowed' : ''}"
                    ${this.currentPage === totalPages ? 'disabled' : ''}
                    data-page="${this.currentPage + 1}">
                <i class="fas fa-chevron-right text-xs"></i>
            </button>
        `;
        
        paginationContainer.innerHTML = paginationHTML;
    }
    
    async deleteFile(fileId) {
        if (!confirm('Are you sure you want to delete this file? This action cannot be undone.')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/file/${fileId}/delete`, {
                method: 'DELETE'
            });
            const data = await response.json();
            
            if (data.success) {
                this.showNotification('File deleted successfully', 'success');
                this.loadFiles();
                this.loadStats();
            } else {
                this.showNotification('Error deleting file: ' + data.message, 'error');
            }
        } catch (error) {
            this.showNotification('Error deleting file: ' + error.message, 'error');
        }
    }
    
    showLoading() {
        document.getElementById('loading-spinner').classList.remove('hidden');
        document.getElementById('files-tbody').innerHTML = '';
    }
    
    hideLoading() {
        document.getElementById('loading-spinner').classList.add('hidden');
    }
    
    showError(message) {
        const tbody = document.getElementById('files-tbody');
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="py-8 text-center text-red-500">
                    <i class="fas fa-exclamation-circle text-2xl mb-2"></i>
                    <p>${message}</p>
                    <button onclick="dashboard.loadFiles()" class="mt-2 text-sm text-green-600 hover:text-green-700">
                        <i class="fas fa-redo mr-1"></i>Retry
                    </button>
                </td>
            </tr>
        `;
    }
    
    showNotification(message, type) {
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg text-white ${
            type === 'success' ? 'bg-green-600' : 'bg-red-600'
        } z-50`;
        notification.innerHTML = `
            <div class="flex items-center">
                <i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'} mr-2"></i>
                <span>${message}</span>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
    
    escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new Dashboard();
});