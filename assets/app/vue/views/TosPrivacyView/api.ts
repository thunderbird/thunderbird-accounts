export interface LegalDocMeta {
  uuid: string;
  document_type: 'tos' | 'privacy';
  version: string;
  content: string;
  accepted: boolean;
}

export interface CurrentLegalDocsResponse {
  documents: LegalDocMeta[];
}

export interface AcceptedDoc {
  document_type: string;
  version: string;
  accepted_at: string;
}

export const getCurrentLegalDocs = async (locale: string): Promise<CurrentLegalDocsResponse> => {
  const response = await fetch(`/api/v1/legal/current/?locale=${encodeURIComponent(locale)}`, {
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': window._page?.csrfToken,
    },
  });
  return await response.json();
};

export const acceptLegalDocs = async (sourceContext: string): Promise<{ responses: AcceptedDoc[] }> => {
  const response = await fetch('/api/v1/legal/accept/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': window._page?.csrfToken,
    },
    body: JSON.stringify({ source_context: sourceContext }),
  });
  return await response.json();
};

export const declineLegalDocs = async (sourceContext: string): Promise<{ redirect_url: string }> => {
  const response = await fetch('/api/v1/legal/decline/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': window._page?.csrfToken,
    },
    body: JSON.stringify({ source_context: sourceContext }),
  });
  return await response.json();
};
