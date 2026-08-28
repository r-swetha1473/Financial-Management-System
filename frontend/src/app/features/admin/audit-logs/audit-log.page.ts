import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { ToastService } from '../../../core/ui/toast.service';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { FilterBarComponent, FilterBarSelect, FilterBarState } from '../../../shared/components/filter-bar/filter-bar.component';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton/loading-skeleton.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { PaginationComponent } from '../../../shared/components/pagination/pagination.component';
import { AuditLog } from '../models/admin.model';
import { AdminApiService } from '../services/admin-api.service';

@Component({
  selector: 'app-audit-log-page',
  standalone: true,
  imports: [
    FormsModule,
    PageHeaderComponent,
    FilterBarComponent,
    PaginationComponent,
    EmptyStateComponent,
    LoadingSkeletonComponent,
  ],
  templateUrl: './audit-log.page.html',
})
export class AuditLogPage implements OnInit {
  private readonly api = inject(AdminApiService);
  private readonly toast = inject(ToastService);
  readonly loading = signal(true);
  readonly error = signal('');
  items: AuditLog[] = [];
  total = 0;
  page = 1;
  entityName = '';
  action = '';
  dateFrom = '';
  dateTo = '';

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.api
      .listAuditLogs({
        page: this.page,
        entityName: this.entityName,
        action: this.action,
        dateFrom: this.dateFrom,
        dateTo: this.dateTo,
      })
      .subscribe({
        next: (result) => {
          this.items = result.items;
          this.total = result.total;
          this.loading.set(false);
        },
        error: () => {
          this.loading.set(false);
          this.error.set('Unable to load audit logs.');
          this.toast.error('Audit logs unavailable');
        },
      });
  }

  get filterSelects(): FilterBarSelect[] {
    return [
      {
        key: 'action',
        label: 'Action',
        blankLabel: 'All actions',
        value: this.action,
        options: [
          { value: 'create', label: 'create' },
          { value: 'update', label: 'update' },
          { value: 'approve', label: 'approve' },
          { value: 'reject', label: 'reject' },
        ],
      },
    ];
  }

  onFilters(state: FilterBarState): void {
    this.entityName = state.search;
    this.action = state.values['action'] ?? '';
    this.page = 1;
    this.load();
  }

  formatWhen(value: string): string {
    if (!value) {
      return '—';
    }
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
  }

  formatActor(row: AuditLog): string {
    if (row.userName && row.userEmail) {
      return `${row.userName} (${row.userEmail})`;
    }
    return row.userName || row.userEmail || '—';
  }

  formatDetails(row: AuditLog): string {
    if (row.details) {
      return row.details;
    }
    const payload = row.newValues ?? row.oldValues;
    return payload ? JSON.stringify(payload) : '—';
  }
}
