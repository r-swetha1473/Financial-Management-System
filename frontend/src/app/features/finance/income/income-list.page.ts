import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { FilterBarComponent, FilterBarSelect, FilterBarState } from '../../../shared/components/filter-bar/filter-bar.component';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton/loading-skeleton.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { PaginationComponent } from '../../../shared/components/pagination/pagination.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge/status-badge.component';
import { InrPipe } from '../../../shared/pipes/inr.pipe';
import { FinanceBannerComponent } from '../components/finance-banner.component';
import { IncomeRecord } from '../models/finance.model';
import { FinanceApiService } from '../services/finance-api.service';

@Component({
  selector: 'app-income-list-page',
  standalone: true,
  imports: [
    RouterLink,
    PageHeaderComponent,
    FinanceBannerComponent,
    FilterBarComponent,
    StatusBadgeComponent,
    PaginationComponent,
    EmptyStateComponent,
    LoadingSkeletonComponent,
    InrPipe,
  ],
  templateUrl: './income-list.page.html',
})
export class IncomeListPage implements OnInit {
  private readonly api = inject(FinanceApiService);
  readonly loading = signal(true);
  readonly error = signal('');
  items: IncomeRecord[] = [];
  total = 0;
  page = 1;
  search = '';
  sourceType = '';

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.api.listIncome({ page: this.page, pageSize: 20 }).subscribe({
      next: (result) => {
        const query = this.search.trim().toLowerCase();
        const filtered = result.items.filter((row) => {
          if (this.sourceType && row.sourceType !== this.sourceType) {
            return false;
          }
          if (!query) {
            return true;
          }
          return (
            row.documentNumber.toLowerCase().includes(query) ||
            (row.customerName ?? '').toLowerCase().includes(query) ||
            this.sourceLabel(row.sourceType).toLowerCase().includes(query)
          );
        });
        this.items = filtered;
        this.total = this.sourceType || query ? filtered.length : result.total;
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.error.set('Unable to load income.');
      },
      });
  }

  get filterSelects(): FilterBarSelect[] {
    return [
      {
        key: 'sourceType',
        label: 'Source',
        blankLabel: 'All cash sources',
        value: this.sourceType,
        options: [
          { value: 'collection', label: 'O2C collections' },
          { value: 'receipt', label: 'Legacy receipts' },
        ],
      },
    ];
  }

  onFilters(state: FilterBarState): void {
    this.search = state.search;
    this.sourceType = state.values['sourceType'] ?? '';
    this.page = 1;
    this.load();
  }

  sourceLabel(type: IncomeRecord['sourceType']): string {
    return type === 'receipt' ? 'Legacy receipt (cash)' : 'O2C collection (cash)';
  }
}
