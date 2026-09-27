import React from 'react';
import { Outlet } from 'react-router-dom';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { CreateAlertModal } from './CreateAlertModal';

export const Layout = () => {
  return (
    <div className="min-h-screen bg-[#F5F6FA] p-4 lg:p-6 flex flex-col font-sans">
      {/* Top Header Card */}
      <Header />

      {/* Main Body: Sidebar + Dynamic Page Content */}
      <div className="flex gap-6 flex-1 items-stretch">
        <Sidebar />
        <main className="flex-1 min-w-0">
          <Outlet />
        </main>
      </div>

      {/* Global Alert Modal */}
      <CreateAlertModal />
    </div>
  );
};
