package org.pvz2.pvz2tool;

import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.method.ScrollingMovementMethod;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import com.chaquo.python.PyObject;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends AppCompatActivity {

    private TextView tvLog;
    private ScrollView scrollLog;
    private EditText etInput;
    private ExecutorService executorService;
    private Handler mainHandler;
    private Python python;
    private PyObject pvz2Module;
    private PyObject scriptInstance;
    private boolean isScriptRunning = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        // 初始化
        executorService = Executors.newSingleThreadExecutor();
        mainHandler = new Handler(Looper.getMainLooper());

        // 初始化UI
        initUI();

        // 初始化Python
        initPython();
    }

    private void initUI() {
        tvLog = findViewById(R.id.tvLog);
        scrollLog = findViewById(R.id.scrollLog);
        etInput = findViewById(R.id.etInput);

        // 设置日志可滚动
        tvLog.setMovementMethod(new ScrollingMovementMethod());

        // 按钮点击事件
        findViewById(R.id.btnLogin).setOnClickListener(v -> runFunction(new String[]{"32"}));
        findViewById(R.id.btnDaily).setOnClickListener(v -> runFunction(new String[]{"30"}));
        findViewById(R.id.btnBatch).setOnClickListener(v -> runFunction(new String[]{"31"}));
        findViewById(R.id.btnPlantUpgrade).setOnClickListener(v -> runFunction(new String[]{"17", "2"}));
        findViewById(R.id.btnCostume).setOnClickListener(v -> runFunction(new String[]{"17", "3"}));
        findViewById(R.id.btnPursuit).setOnClickListener(v -> runFunction(new String[]{"5", "1"}));
        findViewById(R.id.btnEndlessShop).setOnClickListener(v -> runFunction(new String[]{"6", "5"}));
        findViewById(R.id.btnEndlessCoin).setOnClickListener(v -> runFunction(new String[]{"6", "2"}));
        findViewById(R.id.btnGene).setOnClickListener(v -> runFunction(new String[]{"17", "1"}));
        findViewById(R.id.btnActivity).setOnClickListener(v -> runFunction(new String[]{"1"}));
        findViewById(R.id.btnSave).setOnClickListener(v -> runFunction(new String[]{"18"}));
        findViewById(R.id.btnStop).setOnClickListener(v -> stopScript());

        // 清空按钮
        findViewById(R.id.btnClear).setOnClickListener(v -> {
            tvLog.setText("");
            appendLog("日志已清空", "#6b7280");
        });

        // 发送按钮
        findViewById(R.id.btnSend).setOnClickListener(v -> sendInput());

        // 输入框发送事件
        etInput.setOnEditorActionListener((v, actionId, event) -> {
            sendInput();
            return true;
        });
    }

    private void initPython() {
        try {
            if (!Python.isStarted()) {
                Python.start(new AndroidPlatform(this));
            }
            python = Python.getInstance();
            appendLog("Python环境初始化成功", "#16a34a");

            // 导入脚本模块
            try {
                pvz2Module = python.getModule("pvz2_script");
                appendLog("脚本模块加载成功", "#16a34a");
            } catch (Exception e) {
                appendLog("脚本模块加载失败: " + e.getMessage(), "#dc2626");
                appendLog("请确保pvz2_script.py在python目录中", "#6b7280");
            }
        } catch (Exception e) {
            appendLog("Python初始化失败: " + e.getMessage(), "#dc2626");
            e.printStackTrace();
        }
    }

    private void runFunction(String[] menuPath) {
        if (pvz2Module == null) {
            appendLog("脚本模块未加载，无法执行功能", "#dc2626");
            return;
        }

        appendLog("执行功能: " + String.join(" -> ", menuPath), "#7c3aed");

        executorService.execute(() -> {
            try {
                // 重定向Python输出
                ByteArrayOutputStream outputStream = new ByteArrayOutputStream();
                PrintStream printStream = new PrintStream(outputStream);
                PyObject sysModule = python.getModule("sys");
                PyObject oldStdout = sysModule.get("stdout");
                sysModule.put("stdout", printStream);

                try {
                    // 调用脚本的run_function方法
                    // 如果脚本没有这个方法，我们可以直接执行菜单路径
                    PyObject result = pvz2Module.callAttr("run_function", (Object) menuPath);
                    if (result != null) {
                        String resultStr = result.toString();
                        if (!resultStr.isEmpty()) {
                            appendLog(resultStr, null);
                        }
                    }
                } catch (Exception e) {
                    // 如果run_function方法不存在，尝试直接执行
                    appendLog("调用run_function失败，尝试直接执行: " + e.getMessage(), "#f59e0b");
                    try {
                        // 直接执行脚本的主逻辑
                        pvz2Module.callAttr("main");
                    } catch (Exception e2) {
                        appendLog("执行失败: " + e2.getMessage(), "#dc2626");
                    }
                }

                // 恢复标准输出
                sysModule.put("stdout", oldStdout);
                printStream.flush();

                // 输出Python的stdout内容
                String output = outputStream.toString();
                if (!output.isEmpty()) {
                    appendLog(output, null);
                }

            } catch (Exception e) {
                appendLog("执行出错: " + e.getMessage(), "#dc2626");
                e.printStackTrace();
            }
        });
    }

    private void stopScript() {
        if (isScriptRunning) {
            appendLog("正在停止脚本...", "#f59e0b");
            // 这里可以添加停止脚本的逻辑
            isScriptRunning = false;
            appendLog("脚本已停止", "#16a34a");
        } else {
            appendLog("脚本未运行", "#6b7280");
        }
    }

    private void sendInput() {
        String input = etInput.getText().toString().trim();
        if (input.isEmpty()) {
            return;
        }

        appendLog("> " + input, "#2563eb");
        etInput.setText("");

        // 发送输入给脚本
        if (pvz2Module != null && isScriptRunning) {
            executorService.execute(() -> {
                try {
                    pvz2Module.callAttr("send_input", input);
                } catch (Exception e) {
                    appendLog("发送输入失败: " + e.getMessage(), "#dc2626");
                }
            });
        } else {
            appendLog("脚本未运行，请先点击功能按钮启动", "#6b7280");
        }
    }

    private void appendLog(String text, String color) {
        mainHandler.post(() -> {
            String formattedText;
            if (color != null) {
                formattedText = "<font color='" + color + "'>" + text + "</font>";
            } else {
                formattedText = text;
            }

            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.N) {
                tvLog.append(android.text.Html.fromHtml(formattedText + "<br>", android.text.Html.FROM_HTML_MODE_LEGACY));
            } else {
                tvLog.append(android.text.Html.fromHtml(formattedText + "<br>"));
            }

            // 自动滚动到底部
            scrollLog.post(() -> scrollLog.fullScroll(View.FOCUS_DOWN));
        });
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (executorService != null) {
            executorService.shutdown();
        }
    }
}
