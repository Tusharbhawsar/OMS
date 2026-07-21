import type { AffectedCustomer } from "../types";

interface AffectedCustomersPanelProps {
  outageId: string | null;
  customers: AffectedCustomer[];
  isLoading: boolean;
  onClose: () => void;
}

export function AffectedCustomersPanel({ outageId, customers, isLoading, onClose }: AffectedCustomersPanelProps) {
  if (!outageId) {
    return null;
  }

  return (
    <section className="panel customers-panel">
      <div className="panel-heading with-actions">
        <div>
          <p className="eyebrow">Customer impact</p>
          <h2>Affected customers: {outageId}</h2>
        </div>
        <button type="button" className="secondary-button" onClick={onClose}>
          Close
        </button>
      </div>

      {isLoading ? (
        <div className="loading-box">Loading affected customers...</div>
      ) : (
        <div className="table-scroll compact-table">
          <table>
            <thead>
              <tr>
                <th>Priority</th>
                <th>Customer</th>
                <th>Type</th>
                <th>Medical</th>
                <th>Channel</th>
                <th>Phone</th>
                <th>Email</th>
                <th>Service Point</th>
                <th>Circuit</th>
                <th>Transformer</th>
              </tr>
            </thead>
            <tbody>
              {customers.length === 0 ? (
                <tr>
                  <td colSpan={10} className="empty-cell">
                    No affected customers found for this outage.
                  </td>
                </tr>
              ) : (
                customers.map((customer) => (
                  <tr key={`${customer.customer_id}-${customer.service_point_id}`}>
                    <td>{customer.priority}</td>
                    <td>
                      <strong>{customer.full_name}</strong>
                      <span className="subtext mono">{customer.customer_id}</span>
                    </td>
                    <td>{customer.customer_type}</td>
                    <td>{customer.is_medical_baseline ? <span className="medical-chip">Yes</span> : "No"}</td>
                    <td>{customer.channel_name}</td>
                    <td>{customer.phone ?? "-"}</td>
                    <td>{customer.email ?? "-"}</td>
                    <td className="mono">{customer.service_point_id}</td>
                    <td className="mono">{customer.circuit_id}</td>
                    <td className="mono">{customer.transformer_id}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
