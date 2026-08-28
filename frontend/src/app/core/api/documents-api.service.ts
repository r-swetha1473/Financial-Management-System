import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiClientService } from './api-client.service';

export interface StoredDocument {
  id: string;
  organizationId: string;
  entityName: string;
  entityId: string;
  fileName: string;
  mimeType: string;
  fileSize: number;
  storageKey: string | null;
  uploadedBy: string | null;
  createdAt: string;
}

@Injectable({ providedIn: 'root' })
export class DocumentsApiService {
  private readonly api = inject(ApiClientService);

  upload(file: File, entityName: string, entityId: string, kind?: string): Observable<StoredDocument> {
    const body = new FormData();
    body.append('file', file);
    body.append('entityName', entityName);
    body.append('entityId', entityId);
    if (kind) {
      body.append('kind', kind);
    }
    return this.api.postForm<StoredDocument>('/documents', body);
  }

  getContent(documentId: string): Observable<Blob> {
    return this.api.getBlob(`/documents/${documentId}/content`);
  }
}
