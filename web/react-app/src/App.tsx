import React from 'react';
import Header from './components/Header';
import FiltersPanel from './components/FiltersPanel';
import GraphContainer from './components/GraphContainer';
import Tooltip from './components/Tooltip';
import Modal from './components/Modal';
import LogModal from './components/LogModal';

export default function App() {
  return (
    <div className="container">
      <Header />
      <div className="main-content">
        <FiltersPanel />
        <GraphContainer />
      </div>
      <Tooltip />
      <Modal />
      <LogModal />
    </div>
  );
}
