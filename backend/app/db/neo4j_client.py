from neo4j import GraphDatabase

from app.core.config import get_settings


class Neo4jClient:
    def __init__(self):
        settings = get_settings()
        self._driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )

    def verify(self) -> bool:
        self._driver.verify_connectivity()
        return True

    def query(self, cypher: str, params: dict | None = None) -> list[dict]:
        with self._driver.session() as session:
            result = session.run(cypher, params or {})
            return [record.data() for record in result]

    def close(self):
        self._driver.close()


neo4j_client = Neo4jClient()
