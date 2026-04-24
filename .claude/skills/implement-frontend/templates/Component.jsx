// src/components/FeatureComponent.jsx — Plantilla de componente reutilizable
// Props documentadas con JSDoc para componentes con props complejas

/**
 * @param {Object} props
 * @param {string} [props.title] - Título del componente
 * @param {Function} [props.onAction] - Callback para la acción principal
 * @param {React.ReactNode} [props.children] - Contenido interno
 */
export default function FeatureComponent({ title, onAction, children }) {
  return (
    <div>
      {title && <h2>{title}</h2>}
      <div>{children}</div>
      {onAction && (
        <button type="button" onClick={onAction}>
          Acción
        </button>
      )}
    </div>
  );
}
