import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { FilterProvider } from './context/FilterContext';
import { Layout } from './components/Layout';

import { Overview } from './pages/Overview';
import { Transactions } from './pages/Transactions';
import { FraudDetection } from './pages/FraudDetection';
import { BulkFraudDetection } from './pages/BulkFraudDetection';
import { Investigations } from './pages/Investigations';
import { Customers } from './pages/Customers';
import { Merchants } from './pages/Merchants';
import { RulesModels } from './pages/RulesModels';
import { Alerts } from './pages/Alerts';
import { Reports } from './pages/Reports';
import { Compliance } from './pages/Compliance';
import { AdminPanel } from './pages/AdminPanel';

export default function App() {
  return (
    <FilterProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Overview />} />
            <Route path="transactions" element={<Transactions />} />
            <Route path="fraud-detection" element={<FraudDetection />} />
            <Route path="bulk-fraud-detection" element={<BulkFraudDetection />} />
            <Route path="investigations" element={<Investigations />} />
            <Route path="customers" element={<Customers />} />
            <Route path="merchants" element={<Merchants />} />
            <Route path="rules-models" element={<RulesModels />} />
            <Route path="alerts" element={<Alerts />} />
            <Route path="reports" element={<Reports />} />
            <Route path="compliance" element={<Compliance />} />
            <Route path="admin" element={<AdminPanel />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </FilterProvider>
  );
}
