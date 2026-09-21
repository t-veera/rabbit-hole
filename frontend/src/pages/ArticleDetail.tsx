import { useParams, Link } from "react-router-dom";
import ItemReader from "../components/ItemReader";

export default function ArticleDetail() {
  const { id } = useParams<{ id: string }>();
  if (!id) return null;
  return (
    <div>
      <div style={{ marginBottom: 16, display: "flex", justifyContent: "space-between" }}>
        <Link to="/journalism" className="btn subtle">
          &larr; Back to journalism
        </Link>
        <Link className="btn" to={`/split?a=article:${id}`}>
          Open in split view
        </Link>
      </div>
      <ItemReader kind="article" id={id} />
    </div>
  );
}
