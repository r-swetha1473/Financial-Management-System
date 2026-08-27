import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { AuthService } from '../../../core/auth/auth.service';
import { hasPermission } from '../../../core/rbac/permissions';
import { ToastService } from '../../../core/ui/toast.service';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton/loading-skeleton.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { PaginationComponent } from '../../../shared/components/pagination/pagination.component';
import { DocumentMeta } from '../../finance/models/finance.model';
import { FinanceApiService } from '../../finance/services/finance-api.service';

@Component({
  selector: 'app-document-list-page',
  standalone: true,
  imports: [FormsModule, PageHeaderComponent, PaginationComponent, EmptyStateComponent, LoadingSkeletonComponent],
  templateUrl: './document-list.page.html',
})
export class DocumentListPage implements OnInit {
  private readonly api = inject(FinanceApiService);
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

  onFile(event: Event): void {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (!file || !this.canEdit()) {
      return;
    }
    this.api
      .saveDocument({
        entityName: 'workspace',
        entityId: 'workspace',
        fileName: file.name,
        mimeType: file.type || 'application/octet-stream',
        fileSize: `${Math.max(1, Math.round(file.size / 1024))} KB`,
        storageKey: `${this.auth.session()?.organizationId ?? 'org'}/workspace/${file.name}`,
      })
      .subscribe({
        next: () => {
          this.toast.success('Document metadata saved');
          this.load();
        },
        error: (err) => this.toast.error('Save failed', err.message),
      });
  }
}
