import { Injectable, inject } from '@angular/core';

import { AuditStore } from '../../../core/audit/audit.store';
import { addMoney, subtractMoney } from '../../../core/utils/money.util';
import { O2cStore } from '../../o2c/services/o2c.store';
import { P2pStore } from '../../p2p/services/p2p.store';
import { FinanceStore } from './finance.store';

export interface ReportKpi {
  label: string;
  value: string;
  tone?: 'income' | 'expense' | 'cash' | 'receivable' | 'payable';
  format?: 'money' | 'text';
}

export interface ReportColumn {
  key: string;
  label: string;
  type?: 'text' | 'money' | 'status';
}

export interface ReportViewModel {
  key: string;
  title: string;
  subtitle: string;
  note: string;
  kpis: ReportKpi[];
  columns: ReportColumn[];
  rows: Record<string, string>[];
}

@Injectable({ providedIn: 'root' })
export class ReportService {
  private readonly finance = inject(FinanceStore);
  private readonly p2p = inject(P2pStore);
  private readonly o2c = inject(O2cStore);
  private readonly audit = inject(AuditStore);

  build(key: string): ReportViewModel {
    switch (key) {
      case 'p2p':
        return this.p2pReport();
      case 'o2c':
        return this.o2cReport();
      case 'expenses':
        return this.expenseReport();
      case 'income':
        return this.incomeReport();
      case 'payables':
        return this.payablesReport();
      case 'receivables':
        return this.receivablesReport();
      case 'gst':
        return this.gstReport();
      case 'cash-flow':
        return this.cashFlowReport();
      case 'financial-summary':
        return this.financialSummary();
      case 'audit':
        return this.auditReport();
      case 'vendor-expense':
        return this.vendorExpenseReport();
      case 'customer-income':
        return this.customerIncomeReport();
      case 'product-summary':
        return this.productReport();
      case 'invoices':
        return this.invoiceReport();
      case 'receipts':
        return this.receiptReport();
      default:
        return {
          key,
          title: 'Report',
          subtitle: '',
          note: '',
          kpis: [],
          columns: [],
          rows: [],
        };
    }
  }

  gstTotals() {
    const expenses = this.finance.load().expenses.reduce((sum, row) => addMoney(sum, row.gstAmount), '0.00');
    const supplier = this.p2p.load().supplierInvoices.reduce((sum, row) => addMoney(sum, row.gstAmount), '0.00');
    const outputLegacy = this.o2c
      .load()
      .invoices.filter((row) => row.isGstInvoice)
      .reduce((sum, row) => addMoney(sum, row.gstAmount), '0.00');
    const outputO2c = this.o2c.load().salesInvoices.reduce((sum, row) => addMoney(sum, row.gstAmount), '0.00');
    const inputGst = addMoney(expenses, supplier);
    const outputGst = addMoney(outputLegacy, outputO2c);
    return { expenses, supplier, inputGst, outputLegacy, outputO2c, outputGst, net: subtractMoney(outputGst, inputGst) };
  }

  private p2pReport(): ReportViewModel {
    const state = this.p2p.load();
    const invoiceTotal = state.supplierInvoices.reduce((sum, row) => addMoney(sum, row.amount), '0.00');
    const paid = state.payments.filter((row) => row.status === 'completed').reduce((sum, row) => addMoney(sum, row.amount), '0.00');
    const outstanding = state.payables.reduce((sum, row) => addMoney(sum, row.outstanding), '0.00');
    return {
      key: 'p2p',
      title: 'P2P Report',
      subtitle: 'Purchase documents in the current organization.',
      note: 'Header-level documents only. GST on supplier invoices is stored separately.',
      kpis: [
        { label: 'Purchase orders', value: String(state.purchaseOrders.length), tone: 'cash', format: 'text' },
        { label: 'Supplier invoices', value: invoiceTotal, tone: 'payable' },
        { label: 'Payments', value: paid, tone: 'expense' },
        { label: 'Payables outstanding', value: outstanding, tone: 'payable' },
      ],
      columns: [
        { key: 'type', label: 'Document' },
        { key: 'number', label: 'Number' },
        { key: 'party', label: 'Vendor' },
        { key: 'amount', label: 'Amount', type: 'money' },
        { key: 'status', label: 'Status', type: 'status' },
      ],
      rows: [
        ...state.purchaseRequests.map((row) => ({
          type: 'Purchase request',
          number: row.requestNumber,
          party: row.vendorName,
          amount: '0.00',
          status: row.status,
        })),
        ...state.purchaseOrders.map((row) => ({
          type: 'Purchase order',
          number: row.poNumber,
          party: row.vendorName,
          amount: row.totalAmount,
          status: row.status,
        })),
        ...state.supplierInvoices.map((row) => ({
          type: 'Supplier invoice',
          number: row.invoiceNumber,
          party: row.vendorName,
          amount: row.amount,
          status: row.status,
        })),
      ],
    };
  }

  private o2cReport(): ReportViewModel {
    const state = this.o2c.load();
    const invoiced = state.salesInvoices.reduce((sum, row) => addMoney(sum, row.amount), '0.00');
    const collected = state.collections
      .filter((row) => row.status === 'completed')
      .reduce((sum, row) => addMoney(sum, row.amount), '0.00');
    const outstanding = state.receivables.reduce((sum, row) => addMoney(sum, row.outstanding), '0.00');
    return {
      key: 'o2c',
      title: 'O2C Report',
      subtitle: 'Sales cycle documents in the current organization.',
      note: 'O2C sales invoices are separate from existing booking invoices.',
      kpis: [
        { label: 'Quotations', value: String(state.quotations.length), tone: 'cash', format: 'text' },
        { label: 'Sales invoices', value: invoiced, tone: 'income' },
        { label: 'Collections', value: collected, tone: 'income' },
        { label: 'Receivables outstanding', value: outstanding, tone: 'receivable' },
      ],
      columns: [
        { key: 'type', label: 'Document' },
        { key: 'number', label: 'Number' },
        { key: 'party', label: 'Customer' },
        { key: 'amount', label: 'Amount', type: 'money' },
        { key: 'status', label: 'Status', type: 'status' },
      ],
      rows: [
        ...state.quotations.map((row) => ({
          type: 'Quotation',
          number: row.quoteNumber,
          party: row.customerName,
          amount: row.totalAmount,
          status: row.status,
        })),
        ...state.salesOrders.map((row) => ({
          type: 'Sales order',
          number: row.orderNumber,
          party: row.customerName,
          amount: row.totalAmount,
          status: row.status,
        })),
        ...state.salesInvoices.map((row) => ({
          type: 'Sales invoice',
          number: row.invoiceNumber,
          party: row.customerName,
          amount: row.amount,
          status: row.status,
        })),
      ],
    };
  }

  private expenseReport(): ReportViewModel {
    const expenses = this.finance.load().expenses;
    const cost = expenses.reduce((sum, row) => addMoney(sum, row.cost), '0.00');
    const gst = expenses.reduce((sum, row) => addMoney(sum, row.gstAmount), '0.00');
    return {
      key: 'expenses',
      title: 'Expense Report',
      subtitle: 'Operational expenses. GST amount is stored separately and is not added to cost.',
      note: 'These rows are the expenses table, not P2P supplier invoices.',
      kpis: [
        { label: 'Expense cost', value: cost, tone: 'expense' },
        { label: 'GST amount', value: gst, tone: 'payable' },
        { label: 'Rows', value: String(expenses.length), tone: 'cash', format: 'text' },
      ],
      columns: [
        { key: 'date', label: 'Date' },
        { key: 'vendor', label: 'Vendor' },
        { key: 'category', label: 'Category' },
        { key: 'description', label: 'Item' },
        { key: 'cost', label: 'Cost', type: 'money' },
        { key: 'gst', label: 'GST', type: 'money' },
        { key: 'status', label: 'Status', type: 'status' },
      ],
      rows: expenses.map((row) => ({
        date: row.expenseDate,
        vendor: row.vendorName,
        category: row.categoryName,
        description: row.productServiceName,
        cost: row.cost,
        gst: row.gstAmount,
        status: row.status,
      })),
    };
  }

  private incomeReport(): ReportViewModel {
    const o2c = this.o2c.load();
    const invoiced = addMoney(
      o2c.invoices.reduce((sum, row) => addMoney(sum, row.invoiceAmount), '0.00'),
      o2c.salesInvoices.reduce((sum, row) => addMoney(sum, row.amount), '0.00'),
    );
    const cash = addMoney(
      o2c.receipts.reduce((sum, row) => addMoney(sum, row.receiptAmount), '0.00'),
      o2c.collections.filter((row) => row.status === 'completed').reduce((sum, row) => addMoney(sum, row.amount), '0.00'),
    );
    return {
      key: 'income',
      title: 'Income / Sales Report',
      subtitle: 'Invoice amounts (accrual) and receipts/collections (cash), listed separately.',
      note: 'Do not add invoice rows to receipt rows — they are two views of related documents.',
      kpis: [
        { label: 'Invoiced (accrual)', value: invoiced, tone: 'income' },
        { label: 'Collected (cash)', value: cash, tone: 'cash' },
      ],
      columns: [
        { key: 'basis', label: 'Basis' },
        { key: 'type', label: 'Source' },
        { key: 'number', label: 'Document' },
        { key: 'party', label: 'Customer' },
        { key: 'amount', label: 'Amount', type: 'money' },
        { key: 'date', label: 'Date' },
      ],
      rows: [
        ...o2c.invoices.map((row) => ({
          basis: 'Accrual',
          type: 'Existing invoice',
          number: row.invoiceNumber,
          party: row.customerName,
          amount: row.invoiceAmount,
          date: row.invoiceRaisedDate,
        })),
        ...o2c.salesInvoices.map((row) => ({
          basis: 'Accrual',
          type: 'O2C sales invoice',
          number: row.invoiceNumber,
          party: row.customerName,
          amount: row.amount,
          date: row.invoiceDate,
        })),
        ...o2c.receipts.map((row) => ({
          basis: 'Cash',
          type: 'Receipt',
          number: row.invoiceNumber,
          party: o2c.invoices.find((invoice) => invoice.id === row.invoiceId)?.customerName ?? '',
          amount: row.receiptAmount,
          date: row.receiptDate,
        })),
        ...o2c.collections.map((row) => ({
          basis: 'Cash',
          type: 'O2C collection',
          number: row.invoiceNumber,
          party: row.customerName,
          amount: row.amount,
          date: row.collectionDate,
        })),
      ],
    };
  }

  private payablesReport(): ReportViewModel {
    const rows = this.p2p.load().payables;
    return {
      key: 'payables',
      title: 'Payables Report',
      subtitle: 'Outstanding supplier balances created with supplier invoices.',
      note: '',
      kpis: [{ label: 'Outstanding', value: rows.reduce((sum, row) => addMoney(sum, row.outstanding), '0.00'), tone: 'payable' }],
      columns: [
        { key: 'invoice', label: 'Invoice' },
        { key: 'vendor', label: 'Vendor' },
        { key: 'amount', label: 'Amount', type: 'money' },
        { key: 'outstanding', label: 'Outstanding', type: 'money' },
        { key: 'status', label: 'Status', type: 'status' },
      ],
      rows: rows.map((row) => ({
        invoice: row.invoiceNumber,
        vendor: row.vendorName,
        amount: row.amount,
        outstanding: row.outstanding,
        status: row.status,
      })),
    };
  }

  private receivablesReport(): ReportViewModel {
    const rows = this.o2c.load().receivables;
    const legacyOutstanding = this.o2c.load().invoices.map((invoice) => {
      const paid = this.o2c.paidOnLegacyInvoice(this.o2c.load(), invoice.id);
      return {
        invoice: invoice.invoiceNumber,
        customer: invoice.customerName,
        amount: invoice.invoiceAmount,
        outstanding: subtractMoney(invoice.invoiceAmount, paid),
        status: invoice.status,
        source: 'Existing invoice',
      };
    });
    return {
      key: 'receivables',
      title: 'Receivables Report',
      subtitle: 'O2C receivables plus pending on existing invoices.',
      note: 'Existing invoice pending is amount less receipts. O2C receivables are a separate ledger.',
      kpis: [
        {
          label: 'O2C outstanding',
          value: rows.reduce((sum, row) => addMoney(sum, row.outstanding), '0.00'),
          tone: 'receivable',
        },
        {
          label: 'Existing invoice pending',
          value: legacyOutstanding.reduce((sum, row) => addMoney(sum, row.outstanding), '0.00'),
          tone: 'receivable',
        },
      ],
      columns: [
        { key: 'source', label: 'Source' },
        { key: 'invoice', label: 'Invoice' },
        { key: 'customer', label: 'Customer' },
        { key: 'amount', label: 'Amount', type: 'money' },
        { key: 'outstanding', label: 'Outstanding', type: 'money' },
        { key: 'status', label: 'Status', type: 'status' },
      ],
      rows: [
        ...rows.map((row) => ({
          source: 'O2C receivable',
          invoice: row.invoiceNumber,
          customer: row.customerName,
          amount: row.amount,
          outstanding: row.outstanding,
          status: row.status,
        })),
        ...legacyOutstanding,
      ],
    };
  }

  private gstReport(): ReportViewModel {
    const gst = this.gstTotals();
    return {
      key: 'gst',
      title: 'GST Summary',
      subtitle: 'Input and output GST from stored gst_amount fields.',
      note: 'CGST, SGST, and IGST are not split in the current schema. GST is not added to invoice or expense totals.',
      kpis: [
        { label: 'Input GST', value: gst.inputGst, tone: 'payable' },
        { label: 'Output GST', value: gst.outputGst, tone: 'income' },
        { label: 'Net (output − input)', value: gst.net, tone: 'cash' },
      ],
      columns: [
        { key: 'source', label: 'Source' },
        { key: 'kind', label: 'Kind' },
        { key: 'amount', label: 'GST amount', type: 'money' },
      ],
      rows: [
        { source: 'Expenses', kind: 'Input', amount: gst.expenses },
        { source: 'Supplier invoices', kind: 'Input', amount: gst.supplier },
        { source: 'Existing GST invoices', kind: 'Output', amount: gst.outputLegacy },
        { source: 'O2C sales invoices', kind: 'Output', amount: gst.outputO2c },
      ],
    };
  }

  private cashFlowReport(): ReportViewModel {
    const finance = this.finance.load();
    const postedIn = finance.transactions
      .filter((row) => row.transactionType === 'credit')
      .reduce((sum, row) => addMoney(sum, row.amount), '0.00');
    const postedOut = finance.transactions
      .filter((row) => row.transactionType === 'debit')
      .reduce((sum, row) => addMoney(sum, row.amount), '0.00');
    const unpostedIn = addMoney(
      this.o2c.load().receipts.reduce((sum, row) => addMoney(sum, row.receiptAmount), '0.00'),
      this.o2c.load().collections.filter((row) => row.status === 'completed').reduce((sum, row) => addMoney(sum, row.amount), '0.00'),
    );
    const unpostedOut = this.p2p
      .load()
      .payments.filter((row) => row.status === 'completed')
      .reduce((sum, row) => addMoney(sum, row.amount), '0.00');
    return {
      key: 'cash-flow',
      title: 'Cash Flow',
      subtitle: 'Posted bank/cash transactions, plus collections and payments that are not auto-posted.',
      note: 'Credit increases the account (money in). Debit decreases it (money out). P2P payments and O2C collections do not post automatically.',
      kpis: [
        { label: 'Posted in', value: postedIn, tone: 'income' },
        { label: 'Posted out', value: postedOut, tone: 'expense' },
        { label: 'Unposted collections/receipts', value: unpostedIn, tone: 'income' },
        { label: 'Unposted P2P payments', value: unpostedOut, tone: 'expense' },
      ],
      columns: [
        { key: 'source', label: 'Source' },
        { key: 'date', label: 'Date' },
        { key: 'account', label: 'Account / party' },
        { key: 'direction', label: 'Direction' },
        { key: 'amount', label: 'Amount', type: 'money' },
      ],
      rows: [
        ...finance.transactions.map((row) => ({
          source: 'Posted transaction',
          date: row.transactionDate,
          account: row.accountName,
          direction: row.transactionType,
          amount: row.amount,
        })),
        ...this.p2p.load().payments.map((row) => ({
          source: 'P2P payment (unposted)',
          date: row.paymentDate,
          account: row.vendorName,
          direction: 'out',
          amount: row.amount,
        })),
        ...this.o2c.load().collections.map((row) => ({
          source: 'O2C collection (unposted)',
          date: row.collectionDate,
          account: row.customerName,
          direction: 'in',
          amount: row.amount,
        })),
        ...this.o2c.load().receipts.map((row) => ({
          source: 'Invoice receipt (unposted)',
          date: row.receiptDate,
          account: row.invoiceNumber,
          direction: 'in',
          amount: row.receiptAmount,
        })),
      ],
    };
  }

  private financialSummary(): ReportViewModel {
    const gst = this.gstTotals();
    const expenses = this.finance.load().expenses.reduce((sum, row) => addMoney(sum, row.cost), '0.00');
    const cash = this.finance.load().accounts.reduce((sum, row) => addMoney(sum, row.balance), '0.00');
    const invoiced = addMoney(
      this.o2c.load().invoices.reduce((sum, row) => addMoney(sum, row.invoiceAmount), '0.00'),
      this.o2c.load().salesInvoices.reduce((sum, row) => addMoney(sum, row.amount), '0.00'),
    );
    const ap = this.p2p.load().payables.reduce((sum, row) => addMoney(sum, row.outstanding), '0.00');
    const ar = this.o2c.load().receivables.reduce((sum, row) => addMoney(sum, row.outstanding), '0.00');
    return {
      key: 'financial-summary',
      title: 'Financial Summary',
      subtitle: 'Organization-level totals from current records. GST is listed separately from income and expense.',
      note: 'Dashboard seed figures are independent until the backend computes them from these tables.',
      kpis: [
        { label: 'Invoiced income', value: invoiced, tone: 'income' },
        { label: 'Expense cost', value: expenses, tone: 'expense' },
        { label: 'Cash / bank', value: cash, tone: 'cash' },
        { label: 'Receivables', value: ar, tone: 'receivable' },
        { label: 'Payables', value: ap, tone: 'payable' },
      ],
      columns: [
        { key: 'metric', label: 'Metric' },
        { key: 'amount', label: 'Amount', type: 'money' },
      ],
      rows: [
        { metric: 'Invoiced income (accrual)', amount: invoiced },
        { metric: 'Expense cost', amount: expenses },
        { metric: 'Input GST', amount: gst.inputGst },
        { metric: 'Output GST', amount: gst.outputGst },
        { metric: 'Cash and bank balances', amount: cash },
        { metric: 'Payables outstanding', amount: ap },
        { metric: 'O2C receivables outstanding', amount: ar },
      ],
    };
  }

  private auditReport(): ReportViewModel {
    const rows = this.audit.load();
    return {
      key: 'audit',
      title: 'Audit Report',
      subtitle: 'Organization change history from P2P, O2C, finance, and administration.',
      note: 'Entries are written when records are saved in this workspace. Database old_values/new_values require FastAPI persistence.',
      kpis: [{ label: 'Entries', value: String(rows.length), tone: 'cash', format: 'text' }],
      columns: [
        { key: 'date', label: 'Date' },
        { key: 'user', label: 'User' },
        { key: 'action', label: 'Action' },
        { key: 'entity', label: 'Entity' },
        { key: 'summary', label: 'Summary' },
      ],
      rows: rows.map((row) => ({
        date: row.createdAt.length > 10 ? row.createdAt.slice(0, 10) : row.createdAt,
        user: row.userName,
        action: row.action,
        entity: `${row.entityName} ${row.entityId}`,
        summary: row.details ?? '',
      })),
    };
  }

  private vendorExpenseReport(): ReportViewModel {
    const map = new Map<string, { vendor: string; expenses: string; invoices: string }>();
    const add = (vendor: string, field: 'expenses' | 'invoices', amount: string) => {
      const current = map.get(vendor) ?? { vendor, expenses: '0.00', invoices: '0.00' };
      current[field] = addMoney(current[field], amount);
      map.set(vendor, current);
    };
    this.finance.load().expenses.forEach((row) => add(row.vendorName || 'Unassigned', 'expenses', row.cost));
    this.p2p.load().supplierInvoices.forEach((row) => add(row.vendorName, 'invoices', row.amount));
    const rows = [...map.values()];
    return {
      key: 'vendor-expense',
      title: 'Vendor Expense Report',
      subtitle: 'Operational expenses and supplier invoices by vendor, shown as separate columns.',
      note: 'Do not add the two columns unless you intend to combine operational expenses with P2P bills.',
      kpis: [],
      columns: [
        { key: 'vendor', label: 'Vendor' },
        { key: 'expenses', label: 'Expenses', type: 'money' },
        { key: 'invoices', label: 'Supplier invoices', type: 'money' },
      ],
      rows: rows.map((row) => ({ vendor: row.vendor, expenses: row.expenses, invoices: row.invoices })),
    };
  }

  private customerIncomeReport(): ReportViewModel {
    const map = new Map<string, { customer: string; invoiced: string; collected: string }>();
    const add = (customer: string, field: 'invoiced' | 'collected', amount: string) => {
      const current = map.get(customer) ?? { customer, invoiced: '0.00', collected: '0.00' };
      current[field] = addMoney(current[field], amount);
      map.set(customer, current);
    };
    const o2c = this.o2c.load();
    o2c.invoices.forEach((row) => add(row.customerName || 'Unassigned', 'invoiced', row.invoiceAmount));
    o2c.salesInvoices.forEach((row) => add(row.customerName, 'invoiced', row.amount));
    o2c.receipts.forEach((row) =>
      add(o2c.invoices.find((invoice) => invoice.id === row.invoiceId)?.customerName || 'Unassigned', 'collected', row.receiptAmount),
    );
    o2c.collections.forEach((row) => add(row.customerName, 'collected', row.amount));
    return {
      key: 'customer-income',
      title: 'Customer Income Report',
      subtitle: 'Invoiced and collected amounts by customer.',
      note: 'Invoiced and collected are different bases and are not added together.',
      kpis: [],
      columns: [
        { key: 'customer', label: 'Customer' },
        { key: 'invoiced', label: 'Invoiced', type: 'money' },
        { key: 'collected', label: 'Collected', type: 'money' },
      ],
      rows: [...map.values()].map((row) => ({ customer: row.customer, invoiced: row.invoiced, collected: row.collected })),
    };
  }

  private productReport(): ReportViewModel {
    const products = this.finance.load().products;
    const expenses = this.finance.load().expenses;
    const offerings = this.finance.load().offerings;
    return {
      key: 'product-summary',
      title: 'Product Financial Summary',
      subtitle: 'Expense cost by product. Offering amounts are catalog prices, not recognized income.',
      note: 'Invoices are not line-itemed by product in the current schema.',
      kpis: [],
      columns: [
        { key: 'product', label: 'Product' },
        { key: 'expenses', label: 'Expense cost', type: 'money' },
        { key: 'offerings', label: 'Offering catalog', type: 'money' },
      ],
      rows: products.map((product) => ({
        product: product.name,
        expenses: expenses.filter((row) => row.productId === product.id).reduce((sum, row) => addMoney(sum, row.cost), '0.00'),
        offerings: offerings.filter((row) => row.productId === product.id).reduce((sum, row) => addMoney(sum, row.amount), '0.00'),
      })),
    };
  }

  private invoiceReport(): ReportViewModel {
    const o2c = this.o2c.load();
    return {
      key: 'invoices',
      title: 'Invoice Report',
      subtitle: 'Existing invoices and O2C sales invoices. GST is stored separately.',
      note: '',
      kpis: [],
      columns: [
        { key: 'type', label: 'Type' },
        { key: 'number', label: 'Invoice' },
        { key: 'customer', label: 'Customer' },
        { key: 'amount', label: 'Amount', type: 'money' },
        { key: 'gst', label: 'GST', type: 'money' },
        { key: 'status', label: 'Status', type: 'status' },
      ],
      rows: [
        ...o2c.invoices.map((row) => ({
          type: 'Existing invoice',
          number: row.invoiceNumber,
          customer: row.customerName,
          amount: row.invoiceAmount,
          gst: row.isGstInvoice ? row.gstAmount : '0.00',
          status: row.status,
        })),
        ...o2c.salesInvoices.map((row) => ({
          type: 'O2C sales invoice',
          number: row.invoiceNumber,
          customer: row.customerName,
          amount: row.amount,
          gst: row.gstAmount,
          status: row.status,
        })),
      ],
    };
  }

  private receiptReport(): ReportViewModel {
    const o2c = this.o2c.load();
    return {
      key: 'receipts',
      title: 'Receipt Report',
      subtitle: 'Existing invoice receipts and O2C collections by mode and date.',
      note: '',
      kpis: [],
      columns: [
        { key: 'type', label: 'Type' },
        { key: 'number', label: 'Invoice' },
        { key: 'mode', label: 'Mode' },
        { key: 'amount', label: 'Amount', type: 'money' },
        { key: 'date', label: 'Date' },
      ],
      rows: [
        ...o2c.receipts.map((row) => ({
          type: 'Receipt',
          number: row.invoiceNumber,
          mode: row.paymentMode,
          amount: row.receiptAmount,
          date: row.receiptDate,
        })),
        ...o2c.collections.map((row) => ({
          type: 'O2C collection',
          number: row.invoiceNumber,
          mode: row.paymentMode,
          amount: row.amount,
          date: row.collectionDate,
        })),
      ],
    };
  }
}
