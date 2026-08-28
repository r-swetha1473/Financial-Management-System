import { Component, OnInit, computed, inject, signal } from '@angular/core';

import { DocumentsApiService } from '../../../core/api/documents-api.service';
import { AuthService } from '../../../core/auth/auth.service';
import { hasPermission } from '../../../core/rbac/permissions';
import { ToastService } from '../../../core/ui/toast.service';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { FilterBarComponent, FilterBarState } from '../../../shared/components/filter-bar/filter-bar.component';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton/loading-skeleton.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { PaginationComponent } from '../../../shared/components/pagination/pagination.component';
import { DocumentMeta } from '../../finance/models/finance.model';
import { FinanceApiService } from '../../finance/services/finance-api.service';

@Component({
  selector: 'app-document-list-page',
  standalone: true,
  imports: [PageHeaderComponent, FilterBarComponent, PaginationComponent, EmptyStateComponent, LoadingSkeletonComponent],
  templateUrl: './document-list.page.html',
})
export class DocumentListPage implements OnInit {
  private readonly api = inject(FinanceApiService);
  private readonly documents = inject(DocumentsApiService);
  private readonly auth = inject(AuthService);
  private readonly toast = inject(ToastService);
  readonly canEdit = computed(() => hasPermission(this.auth.session()?.role, 'create'));
  readonly loading = signal(true);
  readonly error = signal('');
  items: DocumentMeta[] = [];
  total = 0;
  page = 1;
  search = '';

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.api.listDocuments({ page: this.page, search: this.search }).subscribe({
      next: (result) => {
        this.items = result.items;
        this.total = result.total;
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.error.set('Unable to load documents.');
      },
      });
  }

  onFilters(state: FilterBarState): void {
    this.search = state.search;
    this.page = 1;
    this.load();
  }

  onFile(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    const orgId = this.auth.session()?.organizationId;
    if (!file || !this.canEdit() || !orgId) {
      return;
    }
    this.documents.upload(file, 'organization', orgId).subscribe({
      next: () => {
        this.toast.success('Document uploaded');
        input.value = '';
        this.load();
      },
      error: (err) => this.toast.error('Upload failed', err.message),
    });
  }

  download(row: DocumentMeta): void {
    this.documents.getContent(row.id).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = row.fileName;
        link.click();
        URL.revokeObjectURL(url);
      },
      error: (err) => this.toast.error('Download failed', err.message),
    });
  }
}
