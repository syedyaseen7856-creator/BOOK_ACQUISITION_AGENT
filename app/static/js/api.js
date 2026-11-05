/**
 * API client module for SyllExtract Book Acquisition Agent.
 */

const API = {
  async getHealth() {
    try {
      const res = await fetch("/api/health");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (err) {
      console.warn("API.getHealth error:", err);
      throw err;
    }
  },

  async getSystemStatus() {
    try {
      const res = await fetch("/api/system-status");
      if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch system status`);
      return await res.json();
    } catch (err) {
      console.warn("API.getSystemStatus error:", err);
      throw new Error(err.message || "Cannot connect to acquisition backend.");
    }
  },

  async searchCandidates(query) {
    try {
      const res = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(query)
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || `Search failed with status ${res.status}`);
      }
      return data;
    } catch (err) {
      console.error("API.searchCandidates error:", err);
      throw err;
    }
  },

  async getCandidate(candidateId) {
    try {
      const res = await fetch(`/api/candidates/${encodeURIComponent(candidateId)}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `Candidate lookup failed (${res.status})`);
      return data;
    } catch (err) {
      console.error("API.getCandidate error:", err);
      throw err;
    }
  },

  async approveCandidate(candidateId, payload) {
    try {
      const res = await fetch(`/api/candidates/${encodeURIComponent(candidateId)}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || `Approval submission failed (${res.status})`);
      }
      return data;
    } catch (err) {
      console.error("API.approveCandidate error:", err);
      throw err;
    }
  },

  async requestDownload(candidateId, payload = {}) {
    try {
      const res = await fetch(`/api/candidates/${encodeURIComponent(candidateId)}/download`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || `Download execution failed (${res.status})`);
      }
      return data;
    } catch (err) {
      console.error("API.requestDownload error:", err);
      throw err;
    }
  },

  async getJobStatus(jobId) {
    try {
      const res = await fetch(`/api/jobs/${encodeURIComponent(jobId)}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `Job status check failed (${res.status})`);
      return data;
    } catch (err) {
      console.error("API.getJobStatus error:", err);
      throw err;
    }
  },

  async getApprovals() {
    try {
      const res = await fetch("/api/approvals");
      if (!res.ok) throw new Error(`Failed to load approval audit history (${res.status})`);
      return await res.json();
    } catch (err) {
      console.warn("API.getApprovals error:", err);
      return [];
    }
  }
};
