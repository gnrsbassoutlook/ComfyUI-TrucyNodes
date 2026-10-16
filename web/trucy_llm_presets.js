/**
 * LLM Loader Trucy 大脑节点 · API 预设地址簿前端
 *
 *  - 「＋ 保存为API预设」按钮：把当前远程字段（地址/密钥/模型/超时）POST 到
 *    插件目录 api_presets.json，并即时刷新「API预设」下拉；
 *  - 「API预设」下拉选中预设：立即把预设值回填到地址栏等控件（视觉即所见）；
 *  - 打开工作流时自愈：下拉里的预设已被删除 → 自动复位为（不使用预设）。
 *
 * 纯增强：即便本脚本不生效，后端「保存为预设」文本框 + 运行时套用预设
 * 的路径也完全可用（刷新页面后下拉可见）。
 */
import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const NODE_TYPE = "TrucyLLMLoader";
const PRESET_OFF = "（不使用预设）";
const SAVE_NAME_WIDGET = "保存为预设";
const PRESET_WIDGET = "API预设";

function widget(node, name) {
    return (node?.widgets || []).find((w) => w.name === name) || null;
}

function remoteValues(node) {
    return {
        api_base: widget(node, "api_base")?.value ?? "",
        api_key: widget(node, "api_key")?.value ?? "",
        model: widget(node, "model")?.value ?? "",
        timeout: widget(node, "请求超时秒")?.value ?? 300,
    };
}

function presetsUrl(path) {
    if (typeof api?.apiURL === "function") return api.apiURL(path);
    return path;
}

async function fetchPresets() {
    const resp = await fetch(presetsUrl("/trucyllm/api_presets"));
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    const data = await resp.json();
    return Array.isArray(data.presets) ? data.presets : [];
}

function setWidgetValue(w, value) {
    if (!w) return;
    w.value = value;
    if (typeof w.callback === "function") {
        try { w.callback(value); } catch (e) { /* 忽略 */ }
    }
}

function syncComboIndex(node, combo) {
    if (!Array.isArray(node.widgets_values)) return;
    const idx = node.widgets.indexOf(combo);
    if (idx >= 0) node.widgets_values[idx] = combo.value;
}

function refreshPresetCombo(node, selectName) {
    const combo = widget(node, PRESET_WIDGET);
    if (!combo) return;
    fetchPresets()
        .then((presets) => {
            const names = [PRESET_OFF, ...presets.map((p) => p.name)];
            if (combo.options) combo.options.values = names;
            if (selectName && names.includes(selectName)) {
                combo.value = selectName;
                syncComboIndex(node, combo);
            }
            node.setDirtyCanvas?.(true, true);
            if (typeof app.refreshComboInNodes === "function") {
                try { app.refreshComboInNodes(node); } catch (e) { /* 忽略 */ }
            }
        })
        .catch(() => { /* 静默：下拉保持原样，刷新页面即可 */ });
}

async function savePreset(node) {
    const nameField = widget(node, SAVE_NAME_WIDGET);
    const name = String(nameField?.value || "").trim();
    if (!name) {
        alert("请先在「保存为预设」文本框里填个名称，再点 ＋ 按钮。");
        return;
    }
    const values = remoteValues(node);
    if (!String(values.api_base || "").trim()) {
        alert("api_base 地址栏是空的，没什么可保存的。");
        return;
    }
    try {
        const resp = await fetch(presetsUrl("/trucyllm/api_presets"), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, ...values }),
        });
        if (!resp.ok) {
            alert("保存失败: " + (await resp.text()));
            return;
        }
        refreshPresetCombo(node, name);
    } catch (e) {
        alert("保存失败: " + e);
    }
}

app.registerExtension({
    name: "TrucyLLMLoader.BrainPresets",
    async nodeCreated(node) {
        if (node?.comfyClass !== NODE_TYPE) return;
        // 等一帧让 widgets 就绪
        setTimeout(() => {
            const combo = widget(node, PRESET_WIDGET);
            if (!combo) return;

            // ＋ 保存按钮（serialize:false 由 addWidget("button") 保证不进工作流）
            node.addWidget("button", "＋ 保存为API预设", null, () => savePreset(node));

            // 下拉选中预设 → 立即回填远程控件
            if (!combo.__trucyPresetHooked) {
                combo.__trucyPresetHooked = true;
                const orig = combo.callback;
                combo.callback = function (value) {
                    if (typeof orig === "function") orig.call(this, value);
                    if (!value || value === PRESET_OFF) return;
                    fetchPresets()
                        .then((presets) => {
                            const p = presets.find((item) => item.name === value);
                            if (!p) return;
                            if (p.api_base) setWidgetValue(widget(node, "api_base"), p.api_base);
                            if (p.api_key) setWidgetValue(widget(node, "api_key"), p.api_key);
                            if (p.model) setWidgetValue(widget(node, "model"), p.model);
                            if (p.timeout) setWidgetValue(widget(node, "请求超时秒"), Number(p.timeout) || 300);
                            node.setDirtyCanvas?.(true, true);
                        })
                        .catch(() => { /* 静默：运行时后端仍会套用 */ });
                };
            }

            // 自愈：工作流里的预设已被删除 → 复位，避免执行报 value_not_in_list
            if (combo.value && combo.value !== PRESET_OFF) {
                fetchPresets()
                    .then((presets) => {
                        if (!presets.some((p) => p.name === combo.value)) {
                            combo.value = PRESET_OFF;
                            syncComboIndex(node, combo);
                            node.setDirtyCanvas?.(true, true);
                        }
                    })
                    .catch(() => { /* 静默 */ });
            }
        }, 60);
    },
});
