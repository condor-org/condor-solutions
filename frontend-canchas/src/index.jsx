// src/index.js
import React from 'react';
import ReactDOM from 'react-dom/client';
import BaseLayout from './components/layout/BaseLayout';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <BaseLayout />
  </React.StrictMode>
);
