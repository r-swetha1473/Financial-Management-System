import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

import { FilterBarComponent, FilterBarState } from '../../shared/components/filter-bar/filter-bar.component';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';

interface ReportCard {
  title: string;
  description: string;
  route: string;
}

@Component({
  selector: 'app-reports-page',
  standalone: true,
  imports: [RouterLink, PageHeaderComponent, FilterBarComponent],
  templateUrl: './reports.page.html',
})
export class ReportsPage {
  search = '';
  readonly reports: ReportCard[] = [
    { title: 'Purchase', description: 'Purchase orders and supplier invoices.', route: '/reports/p2p' },
    { title: 'Sales', description: 'Subscribed plans and sales invoices.', route: '/reports/o2c' },
    { title: 'Payables', description: 'Outstanding supplier balances.', route: '/reports/payables' },
    { title: 'Receivables', description: 'Outstanding customer balances.', route: '/reports/receivables' },
    { title: 'Cash Flow', description: 'Cash-basis inflows and outflows.', route: '/reports/cash-flow' },
    { title: 'GST Summary', description: 'Stored gst_amount, no tax engine.', route: '/reports/gst' },
    { title: 'P&L (cash-basis)', description: 'Same formula as dashboard net cash.', route: '/reports/financial-summary' },
  ];

  get visibleReports(): ReportCard[] {
    const query = this.search.trim().toLowerCase();
    if (!query) {
      return this.reports;
    }
    return this.reports.filter(
      (report) => report.title.toLowerCase().includes(query) || report.description.toLowerCase().includes(query),
    );
  }

  onFilters(state: FilterBarState): void {
    this.search = state.search;
  }
}
