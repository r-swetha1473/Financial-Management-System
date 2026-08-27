import { Routes } from '@angular/router';

import { authGuard, guestGuard, permissionGuard, referenceDataGuard } from './core/auth/auth.guard';

function report(path: string, title: string, subtitle: string, reportKey: string) {
  return {
    path,
    loadComponent: () => import('./features/reports/report-view.page').then((m) => m.ReportViewPage),
    data: { title, subtitle, reportKey },
  };
}

export const routes: Routes = [
  {
    path: 'login',
    canActivate: [guestGuard],
    loadComponent: () => import('./features/auth/login/login.page').then((m) => m.LoginPage),
  },
  {
    path: 'forgot-password',
    canActivate: [guestGuard],
    loadComponent: () =>
      import('./features/auth/forgot-password/forgot-password.page').then((m) => m.ForgotPasswordPage),
  },
  {
    path: '',
    canActivate: [authGuard],
    loadComponent: () => import('./core/layout/app-shell/app-shell.component').then((m) => m.AppShellComponent),
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
      {
        path: 'dashboard',
        loadComponent: () => import('./features/dashboard/dashboard.page').then((m) => m.DashboardPage),
      },
      {
        path: 'p2p',
        loadComponent: () => import('./features/p2p/p2p-overview.page').then((m) => m.P2pOverviewPage),
      },
      {
        path: 'p2p/purchase-requests',
        loadComponent: () =>
          import('./features/p2p/purchase-requests/purchase-request-list.page').then((m) => m.PurchaseRequestListPage),
      },
      {
        path: 'p2p/purchase-requests/:id',
        loadComponent: () =>
          import('./features/p2p/purchase-requests/purchase-request-detail.page').then(
            (m) => m.PurchaseRequestDetailPage,
          ),
      },
      {
        path: 'p2p/purchase-orders',
        loadComponent: () =>
          import('./features/p2p/purchase-orders/purchase-order-list.page').then((m) => m.PurchaseOrderListPage),
      },
      {
        path: 'p2p/purchase-orders/:id',
        loadComponent: () =>
          import('./features/p2p/purchase-orders/purchase-order-detail.page').then((m) => m.PurchaseOrderDetailPage),
      },
      {
        path: 'p2p/receipts',
        loadComponent: () =>
          import('./features/p2p/receipts/goods-receipt-list.page').then((m) => m.GoodsReceiptListPage),
      },
      {
        path: 'p2p/receipts/:id',
        loadComponent: () =>
          import('./features/p2p/receipts/goods-receipt-detail.page').then((m) => m.GoodsReceiptDetailPage),
      },
      {
        path: 'p2p/supplier-invoices',
        loadComponent: () =>
          import('./features/p2p/supplier-invoices/supplier-invoice-list.page').then(
            (m) => m.SupplierInvoiceListPage,
          ),
      },
      {
        path: 'p2p/supplier-invoices/:id',
        loadComponent: () =>
          import('./features/p2p/supplier-invoices/supplier-invoice-detail.page').then(
            (m) => m.SupplierInvoiceDetailPage,
          ),
      },
      {
        path: 'p2p/payments',
        loadComponent: () => import('./features/p2p/payments/payment-list.page').then((m) => m.PaymentListPage),
      },
      {
        path: 'p2p/payments/:id',
        loadComponent: () => import('./features/p2p/payments/payment-detail.page').then((m) => m.PaymentDetailPage),
      },
      {
        path: 'p2p/payables',
        loadComponent: () => import('./features/p2p/payables/payable-list.page').then((m) => m.PayableListPage),
      },
      {
        path: 'p2p/payables/:id',
        loadComponent: () => import('./features/p2p/payables/payable-detail.page').then((m) => m.PayableDetailPage),
      },
      {
        path: 'o2c',
        loadComponent: () => import('./features/o2c/o2c-overview.page').then((m) => m.O2cOverviewPage),
      },
      {
        path: 'o2c/quotations',
        loadComponent: () =>
          import('./features/o2c/quotations/quotation-list.page').then((m) => m.QuotationListPage),
      },
      {
        path: 'o2c/quotations/:id',
        loadComponent: () =>
          import('./features/o2c/quotations/quotation-detail.page').then((m) => m.QuotationDetailPage),
      },
      {
        path: 'o2c/sales-orders',
        loadComponent: () =>
          import('./features/o2c/sales-orders/sales-order-list.page').then((m) => m.SalesOrderListPage),
      },
      {
        path: 'o2c/sales-orders/:id',
        loadComponent: () =>
          import('./features/o2c/sales-orders/sales-order-detail.page').then((m) => m.SalesOrderDetailPage),
      },
      {
        path: 'o2c/deliveries',
        loadComponent: () =>
          import('./features/o2c/deliveries/delivery-list.page').then((m) => m.DeliveryListPage),
      },
      {
        path: 'o2c/deliveries/:id',
        loadComponent: () =>
          import('./features/o2c/deliveries/delivery-detail.page').then((m) => m.DeliveryDetailPage),
      },
      {
        path: 'o2c/sales-invoices',
        loadComponent: () =>
          import('./features/o2c/sales-invoices/sales-invoice-list.page').then((m) => m.SalesInvoiceListPage),
      },
      {
        path: 'o2c/sales-invoices/:id',
        loadComponent: () =>
          import('./features/o2c/sales-invoices/sales-invoice-detail.page').then((m) => m.SalesInvoiceDetailPage),
      },
      {
        path: 'o2c/collections',
        loadComponent: () =>
          import('./features/o2c/collections/collection-list.page').then((m) => m.CollectionListPage),
      },
      {
        path: 'o2c/collections/:id',
        loadComponent: () =>
          import('./features/o2c/collections/collection-detail.page').then((m) => m.CollectionDetailPage),
      },
      {
        path: 'o2c/receivables',
        loadComponent: () =>
          import('./features/o2c/receivables/receivable-list.page').then((m) => m.ReceivableListPage),
      },
      {
        path: 'o2c/receivables/:id',
        loadComponent: () =>
          import('./features/o2c/receivables/receivable-detail.page').then((m) => m.ReceivableDetailPage),
      },
      {
        path: 'finance/expenses',
        loadComponent: () =>
          import('./features/finance/expenses/expense-list.page').then((m) => m.ExpenseListPage),
      },
      {
        path: 'finance/income',
        loadComponent: () =>
          import('./features/finance/income/income-list.page').then((m) => m.IncomeListPage),
      },
      {
        path: 'finance/transactions',
        loadComponent: () =>
          import('./features/finance/transactions/transaction-list.page').then((m) => m.TransactionListPage),
      },
      {
        path: 'finance/accounts',
        loadComponent: () =>
          import('./features/finance/accounts/account-list.page').then((m) => m.AccountListPage),
      },
      {
        path: 'finance/gst',
        loadComponent: () => import('./features/finance/gst/gst.page').then((m) => m.GstPage),
      },
      {
        path: 'finance/reconciliation',
        loadComponent: () =>
          import('./features/finance/reconciliation/reconciliation.page').then((m) => m.ReconciliationPage),
      },
      {
        path: 'finance/bookings',
        loadComponent: () =>
          import('./features/finance/bookings/booking-list.page').then((m) => m.BookingListPage),
      },
      {
        path: 'finance/bookings/:id',
        loadComponent: () =>
          import('./features/finance/bookings/booking-detail.page').then((m) => m.BookingDetailPage),
      },
      {
        path: 'finance/invoices',
        loadComponent: () =>
          import('./features/finance/invoices/invoice-list.page').then((m) => m.InvoiceListPage),
      },
      {
        path: 'finance/invoices/:id',
        loadComponent: () =>
          import('./features/finance/invoices/invoice-detail.page').then((m) => m.InvoiceDetailPage),
      },
      {
        path: 'finance/receipts',
        loadComponent: () =>
          import('./features/finance/receipts/receipt-list.page').then((m) => m.ReceiptListPage),
      },
      {
        path: 'finance/receipts/:id',
        loadComponent: () =>
          import('./features/finance/receipts/receipt-detail.page').then((m) => m.ReceiptDetailPage),
      },
      {
        path: 'master/vendors',
        loadComponent: () =>
          import('./features/master/vendors/vendor-list.page').then((m) => m.VendorListPage),
      },
      {
        path: 'master/vendors/:id',
        loadComponent: () =>
          import('./features/master/vendors/vendor-detail.page').then((m) => m.VendorDetailPage),
      },
      {
        path: 'master/customers',
        loadComponent: () =>
          import('./features/master/customers/customer-list.page').then((m) => m.CustomerListPage),
      },
      {
        path: 'master/customers/:id',
        loadComponent: () =>
          import('./features/master/customers/customer-detail.page').then((m) => m.CustomerDetailPage),
      },
      {
        path: 'master/products',
        loadComponent: () =>
          import('./features/master/products/product-list.page').then((m) => m.ProductListPage),
      },
      {
        path: 'master/categories',
        loadComponent: () =>
          import('./features/master/categories/category-list.page').then((m) => m.CategoryListPage),
      },
      {
        path: 'master/services',
        loadComponent: () =>
          import('./features/master/services/service-list.page').then((m) => m.ServiceListPage),
      },
      {
        path: 'reports',
        loadComponent: () => import('./features/reports/reports.page').then((m) => m.ReportsPage),
      },
      report('reports/p2p', 'P2P Report', 'Purchase cycle reporting.', 'p2p'),
      report('reports/o2c', 'O2C Report', 'Sales cycle reporting.', 'o2c'),
      report('reports/expenses', 'Expense Report', 'Spend by vendor, category, and date.', 'expenses'),
      report('reports/income', 'Income / Sales Report', 'Collections and invoiced income.', 'income'),
      report('reports/payables', 'Payables Report', 'Open supplier balances.', 'payables'),
      report('reports/receivables', 'Receivables Report', 'Open customer balances.', 'receivables'),
      report('reports/gst', 'GST Summary', 'Input, output, and tax components.', 'gst'),
      report('reports/cash-flow', 'Cash Flow', 'Bank and cash movement.', 'cash-flow'),
      report('reports/financial-summary', 'Financial Summary', 'Organization-level performance.', 'financial-summary'),
      report('reports/audit', 'Audit Report', 'Read-only financial change history.', 'audit'),
      report('reports/vendor-expense', 'Vendor Expense Report', 'Spend by supplier.', 'vendor-expense'),
      report('reports/customer-income', 'Customer Income Report', 'Revenue by customer.', 'customer-income'),
      report('reports/product-summary', 'Product Financial Summary', 'Income and cost by product.', 'product-summary'),
      report('reports/invoices', 'Invoice Report', 'Invoice status, GST, and pending.', 'invoices'),
      report('reports/receipts', 'Receipt Report', 'Collections by mode and date.', 'receipts'),
      {
        path: 'admin/users',
        canActivate: [permissionGuard('admin')],
        loadComponent: () => import('./features/admin/users/user-list.page').then((m) => m.UserListPage),
      },
      {
        path: 'admin/reference-data',
        canActivate: [referenceDataGuard],
        loadComponent: () =>
          import('./features/admin/reference-data/reference-data.page').then((m) => m.ReferenceDataPage),
      },
      {
        path: 'admin/audit-logs',
        loadComponent: () => import('./features/admin/audit-logs/audit-log.page').then((m) => m.AuditLogPage),
      },
      {
        path: 'admin/documents',
        loadComponent: () =>
          import('./features/admin/documents/document-list.page').then((m) => m.DocumentListPage),
      },
      {
        path: 'admin/settings',
        canActivate: [permissionGuard('admin')],
        loadComponent: () => import('./features/admin/settings/settings.page').then((m) => m.SettingsPage),
      },
    ],
  },
  { path: '**', redirectTo: 'dashboard' },
];
