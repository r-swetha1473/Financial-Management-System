import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
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
    FormsModule,
    RouterLink,
    PageHeaderComponent,
    FinanceBannerComponent,
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
    this.api.listIncome({ page: 1, pageSize: 100, search: this.search }).subscribe({
      next: (result) => {
        const filtered = this.sourceType ? result.items.filter((row) => row.sourceType === this.sourceType) : result.items;
        this.total = filtered.length;
        const start = (this.page - 1) * 10;
        this.items = filtered.slice(start, start + 10);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.error.set('Unable to load income.');
      },
    });
  }

  sourceLabel(type: IncomeRecord['sourceType']): string {
    switch (type) {
      case 'invoice':
        return 'Existing invoice (accrual)';
      case 'sales_invoice':
        return 'O2C sales invoice (accrual)';
      case 'receipt':
        return 'Receipt (cash)';
      case 'collection':
        return 'O2C collection (cash)';
    }
  }
}
