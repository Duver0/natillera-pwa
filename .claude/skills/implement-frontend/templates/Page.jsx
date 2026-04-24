// src/pages/FeaturePage.jsx — Plantilla de página
import { useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import styles from './FeaturePage.module.css';

export default function FeaturePage() {
  const { user, loading } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  if (loading) return <div className={styles.loading}>Cargando...</div>;

  return (
    <div className={styles.container}>
      <h1 className={styles.title}>Feature Page</h1>
      {error && <p className={styles.error}>{error}</p>}
      <div className={styles.content}>
        {/* contenido del feature */}
      </div>
    </div>
  );
}
