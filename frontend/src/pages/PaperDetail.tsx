import { useParams, Link } from "react-router-dom";
import ItemReader from "../components/ItemReader";

export default function PaperDetail() {
  const { id } = useParams<{ id: string }>();
  if (!id) return null;
  return (
    <div>
      <div style={{ marginBottom: 16, display: "flex", justifyContent: "space-between" }}>
        <Link to="/" className="btn subtle">
          &larr; Back to feed
        </Link>
        <Link className="btn" to={`/split?a=paper:${id}`}>
          Open in split view
        </Link>
      </div>
      <ItemReader kind="paper" id={id} />
    </div>
  );
}
