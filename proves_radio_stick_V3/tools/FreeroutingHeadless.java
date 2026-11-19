// Headless Freerouting 2.1 driver. Freerouting's own CLI ignores max passes and
// never writes the session file, and its pass loop oscillates, so drive the batch
// autorouter in chunks and keep the session with the fewest open connections.
// Usage: java -cp freerouting.jar:. FreeroutingHeadless in.dsn out.ses passes [via_cost ripup_cost]
import app.freerouting.autoroute.BatchAutorouter;
import app.freerouting.board.*;
import app.freerouting.core.*;
import app.freerouting.core.scoring.BoardStatistics;
import app.freerouting.interactive.HeadlessBoardManager;
import app.freerouting.settings.RouterSettings;
import java.io.*;
import java.util.Locale;

public class FreeroutingHeadless {
  static final int CHUNK = 5;

  public static void main(String[] a) throws Exception {
    RoutingJob job = new RoutingJob();
    HeadlessBoardManager bm = new HeadlessBoardManager(Locale.US, job);
    try (InputStream in = new FileInputStream(a[0])) {
      bm.loadFromSpecctraDsn(in, new BoardObserverAdaptor(), new ItemIdentificationNumberGenerator());
    }
    RoutingBoard board = bm.get_routing_board();
    RouterSettings rs = new RouterSettings(board);
    // Inner layers (In1 GND, In2 +3V3) are planes: vias only, no tracks.
    for (int i = 1; i < rs.isLayerActive.length - 1; i++) rs.isLayerActive[i] = false;
    if (a.length > 4) {
      rs.scoring.via_costs = Integer.parseInt(a[3]);
      rs.set_start_ripup_costs(Integer.parseInt(a[4]));
    }
    job.board = board;
    job.routerSettings = rs;
    int passes = Integer.parseInt(a[2]), best = Integer.MAX_VALUE;
    byte[] bestSes = null;
    for (int start = 1; start <= passes && best > 0; start += CHUNK) {
      rs.set_start_pass_no(start);
      rs.set_stop_pass_no(start + CHUNK - 1);
      StoppableThread t = new StoppableThread() {
        protected void thread_action() { new BatchAutorouter(job).runBatchLoop(); }
      };
      job.thread = t;
      t.start();
      t.join();
      int open = new BoardStatistics(board).connections.incompleteCount;
      System.out.println("CHUNK " + start + " open " + open);
      if (open < best) {
        best = open;
        ByteArrayOutputStream ses = new ByteArrayOutputStream();
        bm.saveAsSpecctraSessionSes(ses, "v3");
        bestSes = ses.toByteArray();
      }
    }
    try (OutputStream out = new FileOutputStream(a[1])) { out.write(bestSes); }
    System.out.println("BEST open " + best);
  }
}
