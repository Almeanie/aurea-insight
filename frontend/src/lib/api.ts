/**
 * API Client for Aurea Insight
 */

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ApiResponse<T> {
  data: T | null;
  error: string | null;
}

interface ChatResponse {
  message: string;
  citations: string[];
  confidence: number;
}

async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const errorText = await response.text();
      return { data: null, error: errorText || `HTTP ${response.status}` };
    }

    const data = await response.json();
    return { data, error: null };
  } catch (error) {
    return {
      data: null,
      error: error instanceof Error ? error.message : "Unknown error",
    };
  }
}

/**
 * Chat API - Auditor Assistant
 */
export const chatApi = {
  /**
   * Send a message to the Auditor Assistant
   */
  send: async (
    message: string,
    companyId?: string,
    auditId?: string
  ): Promise<ApiResponse<ChatResponse>> => {
    return fetchApi<ChatResponse>("/api/chat/", {
      method: "POST",
      body: JSON.stringify({
        message,
        company_id: companyId,
        audit_id: auditId,
      }),
    });
  },

  /**
   * Clear chat session history
   */
  clearSession: async (companyId: string, auditId?: string): Promise<ApiResponse<{ status: string }>> => {
    const queryParams = auditId ? `?audit_id=${auditId}` : "";
    return fetchApi<{ status: string }>(`/api/chat/session/${companyId}${queryParams}`, {
      method: "DELETE",
    });
  },
};

/**
 * Company API
 */
export const companyApi = {
  /**
   * Create a new company with financial data
   */
  create: async (formData: FormData): Promise<ApiResponse<{ company_id: string }>> => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/company/`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorText = await response.text();
        return { data: null, error: errorText || `HTTP ${response.status}` };
      }

      const data = await response.json();
      return { data, error: null };
    } catch (error) {
      return {
        data: null,
        error: error instanceof Error ? error.message : "Unknown error",
      };
    }
  },

  /**
   * Get company details
   */
  get: async (companyId: string): Promise<ApiResponse<unknown>> => {
    return fetchApi(`/api/company/${companyId}`);
  },

  /**
   * List all companies
   */
  list: async (): Promise<ApiResponse<unknown[]>> => {
    return fetchApi("/api/company/");
  },
};

/**
 * Audit API
 */
export const auditApi = {
  /**
   * Start an audit for a company
   */
  start: async (companyId: string): Promise<ApiResponse<{ audit_id: string }>> => {
    return fetchApi<{ audit_id: string }>(`/api/audit/${companyId}`, {
      method: "POST",
    });
  },

  /**
   * Get audit results
   */
  get: async (auditId: string): Promise<ApiResponse<unknown>> => {
    return fetchApi(`/api/audit/${auditId}`);
  },

  /**
   * Get audit progress
   */
  progress: async (auditId: string): Promise<ApiResponse<unknown>> => {
    return fetchApi(`/api/audit/${auditId}/progress`);
  },
};

/**
 * Export API
 */
export const exportApi = {
  /**
   * Export audit as PDF
   */
  pdf: async (auditId: string): Promise<Blob | null> => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/export/${auditId}/pdf`);
      if (!response.ok) return null;
      return await response.blob();
    } catch {
      return null;
    }
  },

  /**
   * Export audit as CSV
   */
  csv: async (auditId: string): Promise<Blob | null> => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/export/${auditId}/csv`);
      if (!response.ok) return null;
      return await response.blob();
    } catch {
      return null;
    }
  },
};

/**
 * Ownership API
 */
export const ownershipApi = {
  /**
   * Discover ownership structure for a company
   */
  discover: async (companyId: string): Promise<ApiResponse<unknown>> => {
    return fetchApi(`/api/ownership/${companyId}`);
  },
};
