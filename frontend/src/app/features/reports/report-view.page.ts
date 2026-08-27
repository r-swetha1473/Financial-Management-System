import { Component, OnInit, computed, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { AuthService } from '../../core/auth/auth.service';
import { hasPermission } from '../../core/rbac/permissions';
import { downloadCsv } from '../../core/utils/csv.util';
import { EmptyStateComponent } from '../../shared/components/empty-state/empty-state.component';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';
import { StatusBadgeComponent } from '../../shared/components/status-badge/status-badge.component';
import { SummaryCardComponent } from '../../shared/components/summary-card/summary-card.component';
import { InrPipe } from '../../shared/pipes/inr.pipe';
import { ReportService, ReportViewModel } from '../finance/services/report.service';

@Component({
  selector: 'app-report-view-page',
  standalone: true,
  imports: [RouterLink, PageHeaderComponent, SummaryCardComponent, StatusBadgeComponent, EmptyStateComponent, InrPipe],
  templateUrl: './report-view.page.html',
})
export class ReportViewPage implements OnInit {
  private readonly reports = inject(ReportService);
  private readonly route = inject(ActivatedRoute);
  private readonly auth = inject(AuthService);
  readonly canExport = computed(() => hasPermission(this.auth.session()?.role, 'export'));
  model: ReportViewModel | null = null;

  ngOnInit(): void {
    const key = this.route.snapshot.data['reportKey'] as string;
    this.model = this.reports.build(key);
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
