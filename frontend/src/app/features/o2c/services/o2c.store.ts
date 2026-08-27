import { Injectable, inject } from '@angular/core';

import { AuditStore } from '../../../core/audit/audit.store';
import { AuthService } from '../../../core/auth/auth.service';
import { addMoney, compareMoney, subtractMoney } from '../../../core/utils/money.util';
import {
  Booking,
  Collection,
  Customer,
  Delivery,
  InvoiceReceipt,
  LegacyInvoice,
  O2cQuery,
  O2cState,
  PageResult,
  Quotation,
  Receivable,
  SalesInvoice,
  SalesOrder,
} from '../models/o2c.model';
import { DEMO_ORGANIZATION_ID } from '../../../core/seed/ids';
import { createInitialO2cState } from '../seed/o2c.seed';

@Injectable({ providedIn: 'root' })
export class O2cStore {
  private readonly auth = inject(AuthService);
  private readonly audit = inject(AuditStore);

  private key(): string {
    return `bfms_o2c_${this.auth.session()?.organizationId ?? DEMO_ORGANIZATION_ID}`;
  }

  load(): O2cState {
    const raw = localStorage.getItem(this.key());
    if (!raw) {
      const initial = createInitialO2cState();
      this.save(initial);
      return initial;
    }
    try {
      return JSON.parse(raw) as O2cState;
    } catch {
      const initial = createInitialO2cState();
      this.save(initial);
      return initial;
    }
  }

  save(state: O2cState): void {
    localStorage.setItem(this.key(), JSON.stringify(state));
  }

  page<T>(
    items: T[],
    query: O2cQuery,
    searchFields: (item: T) => string,
  ): PageResult<T> {
    const page = query.page ?? 1;
    const pageSize = query.pageSize ?? 10;
    const search = (query.search ?? '').trim().toLowerCase();
    const filtered = items.filter((item) => {
      const row = item as T & { customerId?: string | null; status?: string };
      const matchesSearch = !search || searchFields(item).toLowerCase().includes(search);
      const matchesStatus = !query.status || row.status === query.status;
      const matchesCustomer = !query.customerId || row.customerId === query.customerId;
      return matchesSearch && matchesStatus && matchesCustomer;
    });
    const start = (page - 1) * pageSize;
    return { items: filtered.slice(start, start + pageSize), total: filtered.length, page, pageSize };
  }

  nextId(prefix: string): string {
    return `${prefix}-${Date.now().toString(36)}`;
  }

  customerName(state: O2cState, customerId: string | null): string {
    if (!customerId) {
      return '';
    }
    return state.customers.find((row) => row.id === customerId)?.name ?? '';
  }

  paidOnSalesInvoice(state: O2cState, invoiceId: string): string {
    return state.collections
      .filter((row) => row.salesInvoiceId === invoiceId && row.status === 'completed')
      .reduce((sum, row) => addMoney(sum, row.amount), '0.00');
  }

  outstandingSalesInvoice(state: O2cState, invoice: SalesInvoice): string {
    return subtractMoney(invoice.amount, this.paidOnSalesInvoice(state, invoice.id));
  }

  paidOnLegacyInvoice(state: O2cState, invoiceId: string): string {
    return state.receipts
      .filter((row) => row.invoiceId === invoiceId)
      .reduce((sum, row) => addMoney(sum, row.receiptAmount), '0.00');
  }

  refreshSalesInvoice(state: O2cState, invoiceId: string): void {
    const invoice = state.salesInvoices.find((row) => row.id === invoiceId);
    if (!invoice || invoice.status === 'cancelled') {
      return;
    }
    const outstanding = this.outstandingSalesInvoice(state, invoice);
    if (compareMoney(outstanding, '0.00') <= 0) {
      invoice.status = 'paid';
    } else if (compareMoney(this.paidOnSalesInvoice(state, invoiceId), '0.00') > 0) {
      invoice.status = 'partially_paid';
    } else {
      invoice.status = 'pending';
    }
    const receivable = state.receivables.find((row) => row.sourceId === invoiceId);
    if (receivable) {
      receivable.outstanding = compareMoney(outstanding, '0.00') < 0 ? '0.00' : outstanding;
      receivable.status =
        compareMoney(receivable.outstanding, '0.00') <= 0
          ? 'closed'
          : compareMoney(receivable.outstanding, receivable.amount) < 0
            ? 'partial'
            : 'open';
    }
  }

  refreshLegacyInvoice(state: O2cState, invoiceId: string): void {
    const invoice = state.invoices.find((row) => row.id === invoiceId);
    if (!invoice) {
      return;
    }
    const paid = this.paidOnLegacyInvoice(state, invoiceId);
    const outstanding = subtractMoney(invoice.invoiceAmount, paid);
    if (compareMoney(outstanding, '0.00') <= 0) {
      invoice.status = 'paid';
    } else if (compareMoney(paid, '0.00') > 0) {
      invoice.status = 'partially_paid';
    } else {
      invoice.status = 'pending';
    }
  }

  write<T extends { id: string }>(items: T[], record: T): void {
    const index = items.findIndex((row) => row.id === record.id);
    if (index >= 0) {
      items[index] = record;
    } else {
      items.unshift(record);
    }
  }

  upsertCustomer(record: Customer): Customer {
    const state = this.load();
    const existed = state.customers.some((row) => row.id === record.id);
    this.write(state.customers, record);
    this.save(state);
    this.audit.record('customer', record.id, existed ? 'update' : 'create', `${existed ? 'Updated' : 'Created'} customer ${record.name}`);
    return record;
  }

  upsertQuotation(record: Quotation): Quotation {
    const state = this.load();
    const existed = state.quotations.some((row) => row.id === record.id);
    this.write(state.quotations, record);
    this.save(state);
    this.audit.record('quotation', record.id, existed ? 'update' : 'create', `${existed ? 'Updated' : 'Created'} ${record.quoteNumber}`);
    return record;
  }

  upsertSalesOrder(record: SalesOrder): SalesOrder {
    const state = this.load();
    const existed = state.salesOrders.some((row) => row.id === record.id);
    this.write(state.salesOrders, record);
    if (record.quotationId) {
      const quote = state.quotations.find((row) => row.id === record.quotationId);
      if (quote && quote.status !== 'rejected') {
        quote.status = 'converted';
      }
    }
    this.save(state);
    this.audit.record('sales_order', record.id, existed ? 'update' : 'create', `${existed ? 'Updated' : 'Created'} ${record.orderNumber}`);
    return record;
  }

  upsertDelivery(record: Delivery): Delivery {
    const state = this.load();
    const existed = state.deliveries.some((row) => row.id === record.id);
    this.write(state.deliveries, record);
    const order = state.salesOrders.find((row) => row.id === record.salesOrderId);
    if (order && record.status === 'delivered') {
      order.status = 'fulfilled';
    }
    this.save(state);
    this.audit.record('delivery', record.id, existed ? 'update' : 'create', `${existed ? 'Updated' : 'Created'} ${record.deliveryNumber}`);
    return record;
  }

  upsertSalesInvoice(record: SalesInvoice): SalesInvoice {
    const state = this.load();
    const existed = state.salesInvoices.some((row) => row.id === record.id);
    this.write(state.salesInvoices, record);
    if (!state.receivables.some((row) => row.sourceId === record.id)) {
      state.receivables.unshift({
        id: this.nextId('ar'),
        organizationId: record.organizationId,
        sourceType: 'sales_invoice',
        sourceId: record.id,
        invoiceNumber: record.invoiceNumber,
        customerId: record.customerId,
        customerName: record.customerName,
        amount: record.amount,
        outstanding: record.amount,
        dueDate: record.invoiceDate,
        status: 'open',
        createdAt: record.createdAt,
      });
    }
    this.refreshSalesInvoice(state, record.id);
    this.save(state);
    this.audit.record('sales_invoice', record.id, existed ? 'update' : 'create', `${existed ? 'Updated' : 'Created'} ${record.invoiceNumber}`);
    return record;
  }

  addCollection(record: Collection): Collection {
    const state = this.load();
    const invoice = state.salesInvoices.find((row) => row.id === record.salesInvoiceId);
    if (!invoice) {
      throw new Error('Sales invoice not found.');
    }
    const outstanding = this.outstandingSalesInvoice(state, invoice);
    if (compareMoney(record.amount, outstanding) > 0) {
      throw new Error('Collection cannot exceed the outstanding invoice amount.');
    }
    state.collections.unshift(record);
    this.refreshSalesInvoice(state, invoice.id);
    this.save(state);
    this.audit.record('collection', record.id, 'create', `Recorded collection ${record.amount} for ${record.invoiceNumber}`);
    return record;
  }

  upsertBooking(record: Booking): Booking {
    const state = this.load();
    const existed = state.bookings.some((row) => row.id === record.id);
    this.write(state.bookings, record);
    this.save(state);
    this.audit.record('booking', record.id, existed ? 'update' : 'create', `${existed ? 'Updated' : 'Created'} booking for ${record.customerName}`);
    return record;
  }

  upsertLegacyInvoice(record: LegacyInvoice): LegacyInvoice {
    const state = this.load();
    const existed = state.invoices.some((row) => row.id === record.id);
    this.write(state.invoices, record);
    this.refreshLegacyInvoice(state, record.id);
    this.save(state);
    this.audit.record('invoice_skg', record.id, existed ? 'update' : 'create', `${existed ? 'Updated' : 'Created'} ${record.invoiceNumber}`);
    return record;
  }

  addReceipt(record: InvoiceReceipt): InvoiceReceipt {
    const state = this.load();
    const invoice = state.invoices.find((row) => row.id === record.invoiceId);
    if (!invoice) {
      throw new Error('Invoice not found.');
    }
    const outstanding = subtractMoney(invoice.invoiceAmount, this.paidOnLegacyInvoice(state, invoice.id));
    if (compareMoney(record.receiptAmount, outstanding) > 0) {
      throw new Error('Receipt cannot exceed the outstanding invoice amount.');
    }
    record.pendingAmount = subtractMoney(outstanding, record.receiptAmount);
    state.receipts.unshift(record);
    this.refreshLegacyInvoice(state, invoice.id);
    this.save(state);
    this.audit.record('invoice_receipt', record.id, 'create', `Recorded ${record.paymentMode} receipt ${record.receiptAmount} for ${record.invoiceNumber}`);
    return record;
  }
}
