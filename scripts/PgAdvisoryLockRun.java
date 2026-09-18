// Run a command while holding a Postgres transaction-level advisory lock, serializing
// keycloak-config-cli imports across replicas. The open transaction pins the database
// connection when a transaction-pooling proxy sits between Keycloak and PostgreSQL.
// Runs source-file style on the Keycloak image's bundled Java:
//
//   java -cp <postgresql-driver.jar> PgAdvisoryLockRun.java <command> [args...]
//
// The lock releases on commit, rollback, or connection loss.

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.Statement;
import java.util.Properties;

public class PgAdvisoryLockRun {
    private static final String CACHE_ATTRIBUTE_PREFIX = "de.adorsys.keycloak.config.import-checksum-";
    private static final String REALM_NAME = "tbpro";

    public static void main(String[] args) throws Exception {
        if (args.length == 0) {
            System.err.println("usage: PgAdvisoryLockRun <command> [args...]");
            System.exit(2);
        }

        Connection conn = null;
        int exitCode = 1;
        try {
            conn = lockedConnection();
            boolean cached = cacheMarkerExists(conn);
            System.out.println(
                    cached
                            ? "PgAdvisoryLockRun: revision cache marker found; verifying only."
                            : "PgAdvisoryLockRun: revision cache marker absent; reconciling.");
            ProcessBuilder childBuilder = new ProcessBuilder(args).inheritIO();
            if (cached) {
                childBuilder.environment().put("KEYCLOAK_CONFIG_CACHED", "yes");
            }
            Process child = childBuilder.start();
            exitCode = child.waitFor();

            if (exitCode == 0 && !cacheMarkerExists(conn)) {
                System.err.println("PgAdvisoryLockRun: reconciliation completed without writing its cache marker.");
                exitCode = 1;
            }
            if (exitCode != 0) {
                deleteCacheMarker(conn);
            }
            conn.commit();
        } finally {
            if (conn != null) {
                conn.close();
            }
        }

        System.exit(exitCode);
    }

    // Connect to Keycloak's own database using the same KC_DB_* env vars Keycloak uses
    // (deploy sets KC_DB_PORT, local compose KC_DB_URL_PORT), start a transaction, and take
    // the advisory lock. Blocks until the lock is granted.
    private static Connection lockedConnection() throws Exception {
        String host = System.getenv("KC_DB_URL_HOST");
        if (host == null || host.isEmpty()) {
            throw new IllegalStateException("KC_DB_URL_HOST is not set");
        }
        String port = firstNonEmpty(System.getenv("KC_DB_URL_PORT"), System.getenv("KC_DB_PORT"), "5432");
        String database = firstNonEmpty(System.getenv("KC_DB_URL_DATABASE"), "keycloak");
        String url = "jdbc:postgresql://" + host + ":" + port + "/" + database;

        Properties props = new Properties();
        String user = System.getenv("KC_DB_USERNAME");
        String password = System.getenv("KC_DB_PASSWORD");
        props.setProperty("user", user == null ? "" : user);
        props.setProperty("password", password == null ? "" : password);
        props.setProperty("connectTimeout", "10");
        props.setProperty("loginTimeout", "10");

        Connection conn = DriverManager.getConnection(url, props);
        conn.setAutoCommit(false);
        try (Statement st = conn.createStatement()) {
            System.out.println("PgAdvisoryLockRun: waiting for the reconciliation lock.");
            st.execute("SELECT pg_advisory_xact_lock(hashtext('tbpro-keycloak-config-cli'))");
            try (ResultSet result = st.executeQuery("SELECT pg_backend_pid()")) {
                result.next();
                System.out.println(
                        "PgAdvisoryLockRun: acquired the reconciliation lock on backend "
                                + result.getInt(1) + ".");
            }
        } catch (Exception e) {
            conn.rollback();
            conn.close();
            throw e;
        }
        return conn;
    }

    private static boolean cacheMarkerExists(Connection conn) throws Exception {
        String query = """
                SELECT 1
                  FROM realm_attribute attribute
                  JOIN realm ON realm.id = attribute.realm_id
                 WHERE realm.name = ?
                   AND attribute.name = ?
                """;
        try (PreparedStatement statement = conn.prepareStatement(query)) {
            statement.setString(1, REALM_NAME);
            statement.setString(2, cacheAttributeName());
            try (ResultSet result = statement.executeQuery()) {
                return result.next();
            }
        }
    }

    private static void deleteCacheMarker(Connection conn) throws Exception {
        String query = """
                DELETE FROM realm_attribute
                 WHERE realm_id = (SELECT id FROM realm WHERE name = ?)
                   AND name = ?
                """;
        try (PreparedStatement statement = conn.prepareStatement(query)) {
            statement.setString(1, REALM_NAME);
            statement.setString(2, cacheAttributeName());
            statement.executeUpdate();
        }
    }

    private static String cacheAttributeName() {
        String cacheKey = System.getenv("IMPORT_CACHE_KEY");
        if (cacheKey == null || cacheKey.isEmpty()) {
            throw new IllegalStateException("IMPORT_CACHE_KEY is not set");
        }
        return CACHE_ATTRIBUTE_PREFIX + cacheKey;
    }

    private static String firstNonEmpty(String... values) {
        for (String v : values) {
            if (v != null && !v.isEmpty()) {
                return v;
            }
        }
        return null;
    }
}
