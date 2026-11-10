// Sourcebook's real Astryx component islands. One persistent React/Theme root,
// portals into the existing Rust/JNI UI, no remote scripts, styles or fonts.
import React, {useState} from 'react';
import {createRoot} from 'react-dom/client';
import {createPortal, flushSync} from 'react-dom';
import {Theme} from '@astryxdesign/core/theme';
import {Button} from '@astryxdesign/core/Button';
import {IconButton} from '@astryxdesign/core/IconButton';
import {Icon} from '@astryxdesign/core/Icon';
import {VStack} from '@astryxdesign/core/VStack';
import {HStack} from '@astryxdesign/core/HStack';
import {Card} from '@astryxdesign/core/Card';
import {Text} from '@astryxdesign/core/Text';
import {Heading} from '@astryxdesign/core/Heading';
import {TextInput} from '@astryxdesign/core/TextInput';
import {Selector} from '@astryxdesign/core/Selector';
import {CheckboxInput} from '@astryxdesign/core/CheckboxInput';
import {SegmentedControl, SegmentedControlItem} from '@astryxdesign/core/SegmentedControl';
import {Collapsible} from '@astryxdesign/core/Collapsible';
import {Banner} from '@astryxdesign/core/Banner';
import {Divider} from '@astryxdesign/core/Divider';
import {themes, defaultThemeSlug} from '../src/astryx-themes.js';
import '@astryxdesign/core/reset.css';
import '@astryxdesign/core/astryx.css';
import './astryx.css';

const PRESETS = {
  OpenAI: ['openai', 'https://api.openai.com/v1'],
  Gemini: ['gemini', 'https://generativelanguage.googleapis.com/v1beta'],
  Anthropic: ['anthropic', 'https://api.anthropic.com/v1'],
  OpenRouter: ['openai', 'https://openrouter.ai/api/v1'],
  Groq: ['openai', 'https://api.groq.com/openai/v1'],
  DeepSeek: ['openai', 'https://api.deepseek.com/v1'],
  Mistral: ['openai', 'https://api.mistral.ai/v1'],
  xAI: ['openai', 'https://api.x.ai/v1'],
  Ollama: ['openai', 'http://127.0.0.1:11434/v1'],
  'LM Studio': ['openai', 'http://127.0.0.1:1234/v1'],
  'Optional native runtime': ['native', ''],
};
const ROOT = document.createElement('section');
ROOT.id = 'astryx-root';
ROOT.setAttribute('aria-label', 'Sourcebook design system');
document.body.append(ROOT);
const root = createRoot(ROOT);
const islands = new Map();
let preference = 'system';
let mode = document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light';
function render() {
  flushSync(() => root.render(
    <Theme theme={themes[defaultThemeSlug]} mode={mode}>
      {[...islands].map(([key, {host, node}]) => createPortal(key === 'settings' ? React.cloneElement(node, {appearance: preference}) : node, host, key))}
    </Theme>,
  ));
}
function mount(key, host, node) {
  if (!islands.has(key) || islands.get(key).host !== host) host.replaceChildren();
  islands.set(key, {host, node});
  render();
}
const draft = p => ({
  id: p.id, name: p.name, kind: p.kind, base_url: p.base_url, model: p.model,
  ...(p.api_key ? {api_key: p.api_key} : {}), clear_key: !!p.clear_key,
});
const Hint = ({children}) => <Text type="supporting" as="p">{children}</Text>;

function Provider({provider: p, change, remove, api}) {
  const [models, setModels] = useState([]);
  const [result, setResult] = useState(null);
  const [job, setJob] = useState('');
  async function run(kind) {
    setJob(kind); setResult(null);
    try {
      const response = await api(`ai/${kind}`, 'POST', draft(p));
      if (kind === 'models') {
        setModels(response.models);
        setResult({ok: true, text: `${response.models.length} models found. Choose a model and test the connection.`});
      } else setResult({ok: true, text: `Connected to ${response.model} · ${Math.round(response.latency_ms)} ms. Save to apply.`});
    } catch (error) { setResult({ok: false, text: error.message}); }
    finally { setJob(''); }
  }
  return <Card className="ax-provider-card" padding={4} elevation="none">
    <VStack gap={4}>
      <HStack gap={3} justify="between" vAlign="center">
        <VStack gap={1}>
          <Heading level={3}>{p.name || 'New connection'}</Heading>
          <Text type="supporting">{p.kind === 'native' ? 'Optional on-device model' : 'Your API · your credentials'}</Text>
        </VStack>
        <IconButton label="Remove provider" variant="ghost" size="sm" icon={<Icon icon="close" />} onClick={remove} />
      </HStack>
      <TextInput label="Provider name" value={p.name} onChange={v => change({name: v})} placeholder="Connection name" width="100%" />
      <TextInput label="Model ID" value={p.model} onChange={v => change({model: v})} placeholder="Load models or enter an exact ID" hasSpellCheck={false} width="100%" />
      <TextInput label="API key" type="password" value={p.api_key || ''} onChange={v => change({api_key: v || undefined})} placeholder={p.key_set ? 'Saved key — leave blank to keep' : 'Enter your API key'} autoComplete="off" hasSpellCheck={false} width="100%" />
      <Collapsible trigger="Endpoint & advanced settings" defaultIsOpen={false}>
        <VStack gap={4} paddingBlock={3}>
          <Selector label="API protocol" value={p.kind} options={[{value:'openai', label:'OpenAI-compatible'}, {value:'gemini',label:'Gemini'}, {value:'anthropic',label:'Anthropic'}, {value:'native',label:'On-device text engine'}]} onChange={kind => change({kind, ...(kind === 'gemini' ? {base_url:'https://generativelanguage.googleapis.com/v1beta'} : kind === 'anthropic' ? {base_url:'https://api.anthropic.com/v1'} : {})})} presentation="adaptive" width="100%" />
          <TextInput label="Base URL" type="url" value={p.base_url} onChange={v => change({base_url: v})} hasSpellCheck={false} width="100%" />
          <CheckboxInput label="Remove saved key on save" value={!!p.clear_key} onChange={v => change({clear_key:v})} />
        </VStack>
      </Collapsible>
      <HStack gap={2} wrap="wrap">
        <Button label="Load models" variant="secondary" icon={<Icon icon="search" />} isLoading={job === 'models'} isDisabled={!!job && job !== 'models'} onClick={() => run('models')} />
        <Button label="Test connection" variant="secondary" icon={<Icon icon="check" />} isLoading={job === 'test'} isDisabled={!!job && job !== 'test'} onClick={() => run('test')} />
      </HStack>
      {models.length > 0 && <Selector label="Available models" options={models} value={models.includes(p.model) ? p.model : undefined} onChange={v => change({model:v})} hasSearch presentation="adaptive" width="100%" />}
      {result && <Banner status={result.ok ? 'success' : 'error'} title={result.ok ? 'Connection details' : 'Connection failed'} description={result.text} />}
    </VStack>
  </Card>;
}
function Settings({settings, api, onSaved, onDisconnect, appearance, onAppearance}) {
  const [providers, setProviders] = useState(() => (settings.providers || []).map(p => ({...p})));
  const [assignments, setAssignments] = useState(() => ({...settings.assignments}));
  const [tab, setTab] = useState('connections');
  const [preset, setPreset] = useState('Gemini');
  const [query, setQuery] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [dirty, setDirty] = useState(false);
  const tasks = settings.tasks || ['default','chat','flashcards','quiz','slides','vision','speech','transcription'];
  function update(id, patch) { setDirty(true); setProviders(old => old.map(p => p.id === id ? {...p,...patch} : p)); }
  function add() {
    const id = crypto.randomUUID ? crypto.randomUUID() : 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g,c => {const r=crypto.getRandomValues(new Uint8Array(1))[0]%16;return(c==='x'?r:(r&3|8)).toString(16);});
    const [kind, base_url] = PRESETS[preset];
    if (!providers.length && !assignments.default) setAssignments(old => ({...old, default:id}));
    setProviders(old => [...old,{id,name:preset,kind,base_url,model:kind==='native'?'Optional local AI':''}]);
    setDirty(true);
  }
  async function save() {
    setSaving(true); setError('');
    try { await api('ai','PUT',{providers:providers.map(draft),assignments}); await onSaved(); }
    catch (e) { setError(e.message); }
    finally { setSaving(false); }
  }
  return <VStack gap={0} className="ax-settings">
    <VStack padding={4} className="ax-settings-nav">
      <SegmentedControl label="Settings sections" value={tab} onChange={setTab} layout="fill" size="sm">
        <SegmentedControlItem value="connections" label="AI" />
        <SegmentedControlItem value="routing" label="Routing" />
        <SegmentedControlItem value="app" label="Device" />
      </SegmentedControl>
    </VStack>
    <VStack gap={5} padding={4} className="ax-settings-content">
      {tab === 'connections' && <>
        <VStack gap={2}>
          <Heading level={3}>AI connections</Heading>
          <Hint>Bring your own provider. Discover models and test a small request before saving. No local model download is required for APIs.</Hint>
        </VStack>
        {providers.length === 0 && <Banner status="info" title="Connect your first AI" description="Choose a provider below. Your first connection becomes the default for notebook tasks." />}
        {providers.map(p => <Provider key={p.id} provider={p} change={patch => update(p.id,patch)} api={api} remove={() => {
          if (!confirm('Remove this connection? Changes apply when saved.')) return;
          setProviders(old => old.filter(x => x.id !== p.id));
          setAssignments(old => Object.fromEntries(Object.entries(old).filter(([,v]) => v !== p.id))); setDirty(true);
        }} />)}
        <Divider />
        <Selector label="Provider preset" value={preset} options={Object.keys(PRESETS)} onChange={setPreset} presentation="adaptive" width="100%" />
        <Button label="Add connection" variant="secondary" onClick={add} width="100%" />
        <Hint>Connection tests may incur provider charges. Keys are sent only to the Rust core and your configured endpoint.</Hint>
      </>}
      {tab === 'routing' && <>
        <Heading level={3}>A model for every task</Heading>
        <Hint>Choose a default, then override only the tasks that need a different model. Speech requires an OpenAI-compatible audio endpoint.</Hint>
        <TextInput label="Filter tasks" type="search" value={query} onChange={setQuery} hasClear />
        {tasks.filter(t => t.replaceAll('-',' ').includes(query.toLowerCase())).map(task => <Selector key={task} label={task.replaceAll('-',' ')} options={[{value:'',label:task==='default'?'No default — use environment/native fallback':'Use default connection'},...providers.map(p=>({value:p.id,label:p.name || 'Unnamed',description:p.model || 'Model not selected'}))]} value={assignments[task] || ''} onChange={v => {setAssignments(old=>({...old,[task]:v}));setDirty(true);}} hasSearch={providers.length>5} presentation="adaptive" width="100%" />)}
      </>}
      {tab === 'app' && <>
        <Heading level={3}>Appearance</Heading>
        <SegmentedControl label="Appearance preference" value={appearance} onChange={onAppearance} layout="fill">
          <SegmentedControlItem value="system" label="System" />
          <SegmentedControlItem value="light" label="Light" />
          <SegmentedControlItem value="dark" label="Dark" />
        </SegmentedControl>
        {window.SourcebookAndroid?.reloadWorkspace && <>
          <Divider /><Heading level={3}>Device controls</Heading>
          <Button label="Reload workspace" variant="secondary" icon={<Icon icon="wrench" />} onClick={()=>{if(confirm('Reload and discard unsaved settings?'))window.SourcebookAndroid.reloadWorkspace();}} />
          <Button label="Manage local AI" variant="secondary" onClick={()=>window.SourcebookAndroid.openLocalAI()} />
          <Button label="Cancel local generation" variant="secondary" icon={<Icon icon="stop" />} onClick={()=>window.SourcebookAndroid.cancelAI()} />
          <Hint>Local weights are optional. The bundled text engine supports GGUF; this cancellation control does not cancel cloud requests.</Hint>
        </>}
        <Divider /><Heading level={3}>Privacy & storage</Heading>
        <Hint>{settings.key_storage || 'Saved keys are kept by the Rust core, not browser storage. The app does not add key encryption. Sources go to the provider you assign.'}</Hint>
        <Hint>Notebook exports contain source text and history, but not API keys. Back up before clearing app data.</Hint>
        <Button label="Disconnect workspace" variant="secondary" onClick={onDisconnect} />
        <Divider /><Text type="supporting">Designed with Meta’s Astryx · Sourcebook edition</Text>
      </>}
    </VStack>
    <VStack gap={3} padding={4} className="ax-settings-save">
      {error && <Banner status="error" title="Couldn’t save settings" description={error} />}
      <HStack gap={3} justify="between" vAlign="center" wrap="wrap">
        <Text type="supporting">{dirty ? 'Unsaved changes' : 'Changes apply when saved'}</Text>
        <Button label="Save changes" variant="primary" isLoading={saving} onClick={save} />
      </HStack>
    </VStack>
  </VStack>;
}
function LibraryActions({onCreate,onImport}) {
  return <HStack gap={3} wrap="wrap" className="ax-library-actions">
    <Button label="New notebook" variant="primary" size="lg" onClick={onCreate} />
    <Button label="Add sources" variant="secondary" size="lg" icon={<Icon icon="upload" />} onClick={onImport} />
  </HStack>;
}
function LibraryView({value,onChange}) {
  return <SegmentedControl label="Library view" value={value} onChange={onChange} size="sm">
    <SegmentedControlItem value="list" label="List" icon={<Icon icon="menu" />} />
    <SegmentedControlItem value="spatial" label="3D shelf" icon={<Icon icon="viewColumns" />} />
  </SegmentedControl>;
}
function Studio({tools,onGenerate}) {
  const icons={summary:'copy','study-guide':'viewColumns',faq:'info',briefing:'menu',timeline:'calendar',flashcards:'copy',quiz:'check','mind-map':'arrowsUpDown','data-table':'viewColumns','podcast-script':'microphone',slides:'viewColumns','audio-overview':'microphone','motion-graphic':'externalLink'};
  return <VStack gap={3} className="ax-studio-tools">
    {tools.map(([kind,,label])=><Button key={kind} label={label} variant="secondary" size="lg" icon={<Icon icon={icons[kind] || 'copy'} />} onClick={()=>onGenerate(kind,label)} width="100%" />)}
  </VStack>;
}
window.SourcebookDesign = {
  version:'Astryx 0.7.12 / React 19',
  setAppearance(next, choice) {mode=next; preference=choice || preference; render();},
  mountSettings(host, props) {mount('settings',host,<Settings {...props} />);},
  closeSettings() {if(islands.delete('settings'))render();},
  mountLibrary(host, props) {mount('library-actions',host,<LibraryActions {...props} />);},
  mountView(host, props) {mount('library-view',host,<LibraryView {...props} />);},
  mountStudio(host, props) {mount('studio',host,<Studio {...props} />);},
};
render();
