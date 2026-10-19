import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { CreateAlertModal } from './CreateAlertModal';
import { TransactionDetailDrawer } from './TransactionDetailDrawer';
import { AboutModal } from './AboutModal';
import { useFilter } from '../context/FilterContext';

export const Layout = () => {
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const {
    selectedTransactionId,
    setSelectedTransactionId,
    isAboutModalOpen,
    setIsAboutModalOpen,
  } = useFilter();

  return (
    <div className="app-shell min-h-screen bg-[#F5F8FC] text-slate-800 flex flex-col font-sans">
      {/* Top Header Card */}
      <Header onToggleMobileSidebar={() => setIsMobileSidebarOpen(true)} />

      {/* Main Body: Sidebar + Dynamic Page Content */}
      <div className="flex gap-5 flex-1 items-stretch min-w-0 px-4 pb-4 sm:px-6 sm:pb-6 lg:px-8 lg:pb-8">
        <Sidebar
          isMobileOpen={isMobileSidebarOpen}
          onCloseMobile={() => setIsMobileSidebarOpen(false)}
        />
        <main className="flex-1 min-w-0 overflow-x-hidden">
          <Outlet />
        </main>
      </div>

      {/* Global Modals & Drawers */}
      <CreateAlertModal />
      <TransactionDetailDrawer
        transactionId={selectedTransactionId}
        onClose={() => setSelectedTransactionId(null)}
      />
      <AboutModal
        isOpen={isAboutModalOpen}
        onClose={() => setIsAboutModalOpen(false)}
      />
    </div>
  );
};
