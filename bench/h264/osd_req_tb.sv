// bench/h264/osd_req_tb.sv -- h264/osd_req.sv (interface 0.4, the settings request) against
// tools/osd_req_ref.py (the rule written from the design text): per vector, a menu state and a
// request handed over with a toggle -> err, whether status_set rose (once), status_in (when it
// did). Arms: [err] the result, [set] the pulse, [merge] status_in, [seq] the sequence
// number reported, [count] coverage. $fatal on failure; PASS marker.
`timescale 1ns/1ps
module osd_req_tb;
`define FAIL(arm, msg) begin $display("FAIL [%0s] %0s", arm, msg); $fatal(1); end
reg clk = 0, rst_n = 0; always #18.5 clk = ~clk;
reg [127:0] status; reg [31:0] word; reg tog = 0;
wire [127:0] status_in; wire status_set; wire [7:0] seq; wire [2:0] err; wire [15:0] n_applied;
osd_req dut (.clk(clk), .rst_n(rst_n), .status(status), .set_word(word), .set_tog(tog), .status_in(status_in),
             .status_set(status_set), .seq(seq), .err(err), .n_applied(n_applied));
integer fd, r, n = 0, sets, ne [0:3];
reg [127:0] vs, vout; reg [31:0] vw; integer ve, vset;
string vec;
initial begin
    for (int i = 0; i < 4; i++) ne[i] = 0;
    if (!$value$plusargs("vec=%s", vec)) `FAIL("harness", "+vec= missing")
    fd = $fopen(vec, "r");
    status = '0; word = '0;
    repeat (4) @(posedge clk); rst_n = 1; repeat (4) @(posedge clk);
    forever begin
        r = $fscanf(fd, "%h %h %h %h %h\n", vs, vw, ve, vset, vout);
        if (r != 5) break;
        @(negedge clk); status = vs; word = vw; tog = ~tog;
        sets = 0;
        repeat (8) begin @(posedge clk); #1; if (status_set === 1'b1) sets = sets + 1; end
        if (err !== ve[2:0]) `FAIL("err", $sformatf("vector %0d (word %h): err %0d, want %0d", n, vw, err, ve))
        if (sets !== vset) `FAIL("set", $sformatf("vector %0d: status_set rose %0d times, want %0d", n, sets, vset))
        if (vset && status_in !== vout) `FAIL("merge", $sformatf("vector %0d (word %h): status_in %h, want %h", n, vw, status_in, vout))
        if (seq !== vw[31:24]) `FAIL("seq", $sformatf("vector %0d: seq %h, want %h", n, seq, vw[31:24]))
        ne[ve] = ne[ve] + 1; n = n + 1;
    end
    if (n < 1000 || ne[0] < 100 || ne[1] < 20 || ne[2] < 20 || ne[3] < 20)
        `FAIL("count", $sformatf("coverage: %0d vectors, results %0d / %0d / %0d / %0d", n, ne[0], ne[1], ne[2], ne[3]))
    $display("osd_req_tb: %0d requests identical to the model (applied %0d, range %0d, reserved %0d, empty %0d)", n, ne[0], ne[1], ne[2], ne[3]);
    $display("PASS: osd_req_tb");
    $finish;
end
endmodule
