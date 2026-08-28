import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { AuthService } from '../../core/auth/auth.service';
import { hasPermission } from '../../core/rbac/permissions';
import { downloadCsv } from '../../core/utils/csv.util';
import { EmptyStateComponent } from '../../shared/components/empty-state/empty-state.component';
import { LoadingSkeletonComponent } from '../../shared/components/loading-skeleton/loading-skeleton.component';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';
import { StatusBadgeComponent } from '../../shared/components/status-badge/status-badge.component';
import { SummaryCardComponent } from '../../shared/components/summary-card/summary-card.component';
import { InrPipe } from '../../shared/pipes/inr.pipe';
import { FinanceApiService } from '../finance/services/finance-api.service';
import { ReportViewModel } from '../finance/services/report.service';

@Component({
  selector: 'app-report-view-page',
  standalone: true,
  imports: [
    RouterLink,
    PageHeaderComponent,
    SummaryCardComponent,
    StatusBadgeComponent,
    EmptyStateComponent,
    LoadingSkeletonComponent,
    InrPipe,
  ],
  templateUrl: './report-view.page.html',
})
export class ReportViewPage implements OnInit {
  private readonly api = inject(FinanceApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly auth = inject(AuthService);
  readonly canExport = computed(() => hasPermission(this.auth.session()?.role, 'export'));
  readonly loading = signal(true);
  readonly error = signal('');
  model: ReportViewModel | null = null;

  ngOnInit(): void {
    const key = this.route.snapshot.data['reportKey'] as string;
    this.api.getReport(key).subscribe({
      next: (model) => {
        this.model = model;
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.error.set('Unable to load this report.');
      },
    });
  }

  exportCsv(): void {
    if (!this.model || !this.canExport()) {
      return;
    }
    downloadCsv(
      `${this.model.key}-report.csv`,
      this.model.columns.map((column) => column.label),
      this.model.rows.map((row) => this.model!.columns.map((column) => row[column.key] ?? '')),
    );
  }
}
