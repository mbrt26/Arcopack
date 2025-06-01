import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Container, CssBaseline, Box } from '@mui/material';
import OrderList from './components/orders/OrderList';
import OrderForm from './components/orders/OrderForm';

function App() {
  return (
    <Router>
      <CssBaseline />
      <Container maxWidth="lg">
        <Box sx={{ mt: 4, mb: 4 }}>
          <Routes>
            <Route path="/orders" element={<OrderList />} />
            <Route path="/orders/new" element={<OrderForm />} />
            <Route path="/orders/:id/edit" element={<OrderForm />} />
          </Routes>
        </Box>
      </Container>
    </Router>
  );
}

export default App;
