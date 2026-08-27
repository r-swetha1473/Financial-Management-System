import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';

interface ReportCard {
  title: string;
  description: string;
  route: string;
}

@Component({
  selector: 'app-reports-page',
  standalone: true,
  imports: [RouterLink, PageHeaderComponent],
  templateUrl: './reports.page.html',
})
export class ReportsPage {
  readonly reports: ReportCard[] = [
    { title: 'P2P Report', description: 'Purchase requests through payables.', route: '/reports/p2p' },
    { title: 'O2C Report', description: 'Quotations through collections.', route: '/reports/o2c' },
    { title: 'Expense Report', description: 'Operating and procurement spend.', route: '/reports/expenses' },
    { title: 'Income / Sales Report', description: 'Sales invoices and collections.', route: '/reports/income' },
    { title: 'Payables', description: 'Outstanding supplier balances.', route: '/reports/payables' },
    { title: 'Receivables', description: 'Outstanding customer balances.', route: '/reports/receivables' },
    { title: 'GST Summary', description: 'Input, output, CGST, SGST, IGST.', route: '/reports/gst' },
    { title: 'Cash Flow', description: 'Bank and cash movement.', route: '/reports/cash-flow' },
    { title: 'Financial Summary', description: 'Organization-level performance.', route: '/reports/financial-summary' },
    { title: 'Audit Report', description: 'Organization change history.', route: '/reports/audit' },
    { title: 'Vendor Expense Report', description: 'Spend by supplier.', route: '/reports/vendor-expense' },
    { title: 'Customer Income Report', description: 'Revenue by customer.', route: '/reports/customer-income' },
    { title: 'Product Financial Summary', description: 'Income and cost by product.', route: '/reports/product-summary' },
    { title: 'Invoice Report', description: 'Sales invoice status and GST.', route: '/reports/invoices' },
    { title: 'Receipt Report', description: 'Collections by mode and date.', route: '/reports/receipts' },
  ];
}
