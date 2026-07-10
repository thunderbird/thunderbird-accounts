// Run a command while holding a Postgres session-level advisory lock, serializing
// keycloak-config-cli imports across replicas (see apply-mfa-config.sh for the deploy-race
// background). Runs source-file style on the Keycloak image's bundled Java — no compile
// step, no dependencies beyond Keycloak's own bundled Postgres JDBC driver:
//
//   java -cp <postgresql-driver.jar> PgAdvisoryLockRun.java <command> [args...]
//
// The lock is tied to the JDBC session, so it releases the moment this process exits —
// including abnormal death — and can never wedge a future deploy.
//
// Fail-soft contract: if the DB is unreachable or the lock can't be taken, log a warning
// and run the command anyway, without the lock. A lock-infra problem must not stop the
// config from being applied; the command's own exit code is always propagated.

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.Statement;
import java.util.Properties;

public class PgAdvisoryLockRun {
    public static void main(String[] args) throws Exception {
        if (args.length == 0) {
            System.err.println("usage: PgAdvisoryLockRun <command> [args...]");
            System.exit(2);
        }

        Connection conn = null;
        try {
            conn = lockedConnection();
        } catch (Exception e) {
            System.err.println("PgAdvisoryLockRun: could not take the advisory lock ("
                    + e + "); running the command without it.");
        }

        try {
            Process child = new ProcessBuilder(args).inheritIO().start();
            System.exit(child.waitFor());
        } finally {
            // Unreached on the normal path (System.exit above ends the JVM, closing the
            // session and releasing the lock); kept for clarity if the start itself throws.
            if (conn != null) {
                conn.close();
            }
        }
    }

    // Connect to Keycloak's own database using the same KC_DB_* env vars Keycloak uses
    // (deploy sets KC_DB_PORT, local compose KC_DB_URL_PORT), then take the advisory lock.
    // hashtext() gives a stable key so every replica — and any psql-based caller — contends
    // on the same lock. Blocks until the lock is granted.
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
        try (Statement st = conn.createStatement()) {
            st.execute("SELECT pg_advisory_lock(hashtext('tbpro-keycloak-config-cli'))");
        } catch (Exception e) {
            conn.close();
            throw e;
        }
        return conn;
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
