import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';

import { ApiClientService, ApiError } from '../../../core/api/api-client.service';
import { subtractMoney } from '../../../core/utils/money.util';
import {
  Booking,
  Collection,
  Customer,
  Delivery,
  InvoiceReceipt,
  LegacyInvoice,
  O2cQuery,
  OfferingRef,
  PageResult,
  PlanRef,
  Quotation,
  Receivable,
  SalesInvoice,
  SalesOrder,
} from '../models/o2c.model';
import { O2cStore } from './o2c.store';

@Injectable({ providedIn: 'root' })
export class O2cApiService {
  private readonly api = inject(ApiClientService);
  private readonly store = inject(O2cStore);

  listCustomers(query: O2cQuery = {}): Observable<PageResult<Customer>> {
    return this.api.getPaginated<Customer>('/o2c/customers', {
      page: query.page ?? 1,
      page_size: query.pageSize ?? 20,
    });
  }
  getCustomer(id: string): Observable<Customer | null> {
    return this.api.get<Customer>(`/o2c/customers/${id}`);
  }
  saveCustomer(
    payload: Omit<Customer, 'id' | 'organizationId' | 'createdAt'> & {
      id?: string;
    },
  ): Observable<Customer> {
    if (payload.id) {
      return throwError(
        () =>
          ({
            code: '501',
            message: 'Updating a customer is not supported by the API yet.',
          }) satisfies ApiError,
      );
    }
    return this.api.post<Customer>('/o2c/customers', {
      name: payload.name,
      address: payload.address || null,
      gstin: payload.gstin || null,
      state: payload.state || null,
      creditLimit: payload.creditLimit || null,
      phone: payload.phone || null,
      driversLicenseNumber: payload.driversLicenseNumber || null,
    });
  }

  offerings(): OfferingRef[] {
    return this.store.load().offerings;
  }
  plans(): PlanRef[] {
    return this.store.load().plans;
  }

  listQuotations(query: O2cQuery = {}): Observable<PageResult<Quotation>> {
    return this.api.getPaginated<Quotation>('/o2c/quotations', {
      page: query.page ?? 1,
      page_size: query.pageSize ?? 20,
      customer_id: query.customerId,
      status: query.status,
      search: query.search,
    });
  }
  getQuotation(id: string): Observable<Quotation | null> {
    return this.api.get<Quotation>(`/o2c/quotations/${id}`);
  }
  saveQuotation(
    payload: Omit<Quotation, 'id' | 'organizationId' | 'createdAt' | 'customerName'> & { id?: string },
  ): Observable<Quotation> {
    if (payload.id) {
      return throwError(
        () =>
          ({
            code: '501',
            message: 'Updating a subscribed plan is not supported by the API yet.',
          }) satisfies ApiError,
      );
    }
    return this.api.post<Quotation>('/o2c/quotations', {
      customerId: payload.customerId,
      quoteDate: payload.quoteDate,
      validUntil: payload.validUntil || null,
      totalAmount: payload.totalAmount,
      status: payload.status,
      planDuration: payload.planDuration,
      billingCycle: payload.billingCycle,
      depositAmount: payload.depositAmount,
    });
  }

  acceptQuotation(id: string): Observable<Quotation> {
    return this.api.patch<Quotation>(`/o2c/quotations/${id}/accept`);
  }

  rejectQuotation(id: string): Observable<Quotation> {
    return this.api.patch<Quotation>(`/o2c/quotations/${id}/reject`);
  }

  listSalesOrders(query: O2cQuery = {}): Observable<PageResult<SalesOrder>> {
    return this.api.getPaginated<SalesOrder>('/o2c/sales-orders', {
      page: query.page ?? 1,
      page_size: query.pageSize ?? 20,
      customer_id: query.customerId,
      status: query.status,
      search: query.search,
    });
  }
  getSalesOrder(id: string): Observable<SalesOrder | null> {
    return this.api.get<SalesOrder>(`/o2c/sales-orders/${id}`);
  }
  saveSalesOrder(
    payload: Omit<SalesOrder, 'id' | 'organizationId' | 'createdAt' | 'customerName' | 'quoteNumber'> & { id?: string },
  ): Observable<SalesOrder> {
    if (payload.id) {
      return throwError(
        () =>
          ({
            code: '501',
            message: 'Updating a sales order is not supported by the API yet.',
          }) satisfies ApiError,
      );
    }
    return this.api.post<SalesOrder>('/o2c/sales-orders', {
      customerId: payload.customerId,
      quotationId: payload.quotationId || null,
      orderDate: payload.orderDate,
      totalAmount: payload.totalAmount,
      status: payload.status,
    });
  }

  listDeliveries(query: O2cQuery = {}): Observable<PageResult<Delivery>> {
    return this.api.getPaginated<Delivery>('/o2c/deliveries', {
      page: query.page ?? 1,
      page_size: query.pageSize ?? 20,
    });
  }
  getDelivery(id: string): Observable<Delivery | null> {
    return this.api.get<Delivery>(`/o2c/deliveries/${id}`);
  }
  saveDelivery(
    payload: Omit<Delivery, 'id' | 'organizationId' | 'createdAt' | 'orderNumber' | 'customerId' | 'customerName'> & {
      id?: string;
    },
  ): Observable<Delivery> {
    if (payload.id) {
      return throwError(
        () =>
          ({
            code: '501',
            message: 'Updating a delivery is not supported by the API yet.',
          }) satisfies ApiError,
      );
    }
    return this.api.post<Delivery>('/o2c/deliveries', {
      salesOrderId: payload.salesOrderId,
      deliveryDate: payload.deliveryDate,
      status: payload.status,
    });
  }

  listSalesInvoices(query: O2cQuery = {}): Observable<PageResult<SalesInvoice>> {
    return this.api.getPaginated<SalesInvoice>('/o2c/sales-invoices', {
      page: query.page ?? 1,
      page_size: query.pageSize ?? 20,
    });
  }
  getSalesInvoice(id: string): Observable<SalesInvoice | null> {
    return this.api.get<SalesInvoice>(`/o2c/sales-invoices/${id}`);
  }
  saveSalesInvoice(
    payload: Omit<
      SalesInvoice,
      'id' | 'organizationId' | 'createdAt' | 'customerName' | 'orderNumber' | 'deliveryNumber' | 'approvalStatus' | 'outstanding'
    > & { id?: string },
  ): Observable<SalesInvoice> {
    if (payload.id) {
      return throwError(
        () =>
          ({
            code: '501',
            message: 'Updating a sales invoice is not supported by the API yet.',
          }) satisfies ApiError,
      );
    }
    return this.api.post<SalesInvoice>('/o2c/sales-invoices', {
      deliveryId: payload.deliveryId,
      customerId: payload.customerId || null,
      salesOrderId: payload.salesOrderId || null,
      invoiceDate: payload.invoiceDate,
      amount: payload.amount,
      gstAmount: payload.gstAmount,
    });
  }
  approveSalesInvoice(id: string): Observable<SalesInvoice> {
    return this.api.patch<SalesInvoice>(`/o2c/sales-invoices/${id}/approve`);
  }
  rejectSalesInvoice(id: string): Observable<SalesInvoice> {
    return this.api.patch<SalesInvoice>(`/o2c/sales-invoices/${id}/reject`);
  }

  listCollections(query: O2cQuery = {}): Observable<PageResult<Collection>> {
    return this.api.getPaginated<Collection>('/o2c/collections', {
      page: query.page ?? 1,
      page_size: query.pageSize ?? 20,
    });
  }
  getCollection(id: string): Observable<Collection | null> {
    return this.api.get<Collection>(`/o2c/collections/${id}`);
  }
  createCollection(
    payload: Omit<Collection, 'id' | 'organizationId' | 'createdAt' | 'invoiceNumber' | 'customerId' | 'customerName'>,
  ): Observable<Collection> {
    return this.api.post<Collection>('/o2c/collections', {
      salesInvoiceId: payload.salesInvoiceId,
      collectionDate: payload.collectionDate,
      amount: payload.amount,
      paymentMode: payload.paymentMode,
    });
  }

  listReceivables(query: O2cQuery = {}): Observable<PageResult<Receivable>> {
    return this.api.getPaginated<Receivable>('/o2c/receivables', {
      page: query.page ?? 1,
      page_size: query.pageSize ?? 20,
    });
  }
  getReceivable(id: string): Observable<Receivable | null> {
    return this.api.get<Receivable>(`/o2c/receivables/${id}`);
  }

  salesInvoiceOutstanding(invoice: Pick<SalesInvoice, 'amount' | 'outstanding'> | null) {
    if (!invoice) {
      return null;
    }
    const outstanding = invoice.outstanding ?? invoice.amount;
    return { invoiceAmount: invoice.amount, paid: subtractMoney(invoice.amount, outstanding), outstanding };
  }

  listBookings(query: O2cQuery = {}): Observable<PageResult<Booking>> {
    return this.api.getPaginated<Booking>('/bookings', {
      page: query.page ?? 1,
      page_size: query.pageSize ?? 20,
      customer_id: query.customerId,
    });
  }
  getBooking(id: string): Observable<Booking | null> {
    return this.api.get<Booking>(`/bookings/${id}`);
  }
  saveBooking(
    payload: Omit<Booking, 'id' | 'organizationId' | 'createdAt' | 'customerName' | 'offeringName'> & { id?: string },
  ): Observable<Booking> {
    if (payload.id) {
      return throwError(
        () =>
          ({
            code: '501',
            message: 'Updating a booking is not supported by the API yet.',
          }) satisfies ApiError,
      );
    }
    if (!payload.customerId) {
      return throwError(() => ({ code: '400', message: 'Customer is required.' } satisfies ApiError));
    }
    return this.api.post<Booking>('/bookings', {
      offeringId: payload.offeringId || null,
      customerId: payload.customerId,
      bookingStartDate: payload.bookingStartDate,
      bookingEndDate: payload.bookingEndDate || null,
      securityPaid: payload.securityPaid,
    });
  }

  listInvoices(query: O2cQuery = {}): Observable<PageResult<LegacyInvoice>> {
    return this.api.getPaginated<LegacyInvoice>('/invoices', {
      page: query.page ?? 1,
      page_size: query.pageSize ?? 20,
      customer_id: query.customerId,
    });
  }
  getInvoice(id: string): Observable<LegacyInvoice | null> {
    return this.api.get<LegacyInvoice>(`/invoices/${id}`);
  }
  saveInvoice(
    payload: Omit<
      LegacyInvoice,
      'id' | 'organizationId' | 'createdAt' | 'customerName' | 'bookingLabel' | 'planName' | 'status' | 'paid' | 'outstanding'
    > & { id?: string },
  ): Observable<LegacyInvoice> {
    if (payload.id) {
      return throwError(
        () =>
          ({
            code: '501',
            message: 'Updating an invoice is not supported by the API yet.',
          }) satisfies ApiError,
      );
    }
    return this.api.post<LegacyInvoice>('/invoices', {
      invoiceNumber: payload.invoiceNumber || null,
      customerId: payload.customerId || null,
      bookingId: payload.bookingId || null,
      planId: null,
      invoiceRaisedDate: payload.invoiceRaisedDate,
      securityAmountDeposited: payload.securityAmountDeposited,
      invoiceAmount: payload.invoiceAmount,
      isGstInvoice: payload.isGstInvoice,
      gstAmount: payload.gstAmount,
    });
  }

  listReceipts(query: O2cQuery = {}): Observable<PageResult<InvoiceReceipt>> {
    return this.api.getPaginated<InvoiceReceipt>('/receipts', {
      page: query.page ?? 1,
      page_size: query.pageSize ?? 20,
    });
  }
  getReceipt(id: string): Observable<InvoiceReceipt | null> {
    return this.api.get<InvoiceReceipt>(`/receipts/${id}`);
  }
  createReceipt(
    payload: Omit<InvoiceReceipt, 'id' | 'organizationId' | 'createdAt' | 'invoiceNumber' | 'pendingAmount' | 'enteredBy'> & {
      enteredBy?: string;
    },
  ): Observable<InvoiceReceipt> {
    if (payload.paymentMode === 'UPI' && !/^\d{4}$/.test(payload.transactionLast4)) {
      return throwError(() => ({ code: '400', message: 'UPI receipts require exactly 4 digits.' } satisfies ApiError));
    }
    return this.api.post<InvoiceReceipt>('/receipts', {
      invoiceId: payload.invoiceId,
      receiptDate: payload.receiptDate,
      receiptAmount: payload.receiptAmount,
      paymentMode: payload.paymentMode,
      transactionLast4: payload.paymentMode === 'UPI' ? payload.transactionLast4 : null,
    });
  }

  legacyInvoiceOutstanding(invoice: Pick<LegacyInvoice, 'invoiceAmount' | 'paid' | 'outstanding'> | null) {
    if (!invoice) {
      return null;
    }
    const outstanding = invoice.outstanding ?? invoice.invoiceAmount;
    const paid = invoice.paid ?? subtractMoney(invoice.invoiceAmount, outstanding);
    return { invoiceAmount: invoice.invoiceAmount, paid, outstanding };
  }
}
