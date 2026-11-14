import java.io.*;
import java.util.*;
import java.util.zip.*;

/**
 * DeckWriter — writes a PowerPoint 2007 deck from a plain-text layout script.
 *
 * WHY THIS EXISTS
 * ---------------
 * DeckCraft 0.21.1 can lay out text boxes, but it has no command for setting a text
 * run's font, size or colour once the box exists (its schema exposes formatting for
 * transparency, highlight, outline and anchor, but not type). insert.textBox accepts
 * only rect and text. So every slide arrived in the theme's default type on the
 * theme's blue accent — which is not a deck, it is a placeholder.
 *
 * This writer emits the same twelve slides with real runs: font family, size, colour
 * and letter-spacing per run, plus pictures at exact placements. It uses nothing but
 * the JDK (the ubuntu runner ships a JDK), so it runs in the same workflow.
 *
 * In the workflow, DeckCraft still composes the deck first — it produces the .pptx
 * and its PDF export, and those stay as the DeckCraft artefact. This writer produces
 * the deck that is actually sent.
 *
 * USAGE:  java DeckWriter.java <script.txt> <out.pptx>
 *
 * SCRIPT FORMAT (one directive per line, '#' comments):
 *   size 1280 720
 *   slide
 *   bg    0B0C0E
 *   text  <x> <y> <w> <h> <size%> <colour> <font> <tracking> <flags> | <content>
 *         tracking is 1/100 pt; flags are a subset of B I (bold, italic)
 *         '\n' in content starts a new paragraph
 *   pic   <x> <y> <w> <h> <path>
 *
 * Coordinates are in points on the 1280x720 grid. Font size is given in points.
 */
public class DeckWriter {

  static final int EMU = 12700;             // EMU per point
  static StringBuilder out = new StringBuilder();
  static int shapeId = 2;
  static int relId = 2;
  static int slideNo = 0;
  static List<int[]> sizes = new ArrayList<>();   // width, height per slide in pt
  static List<String> bodies = new ArrayList<>();
  static List<List<String[]>> media = new ArrayList<>(); // per slide: [relId, path]
  static int W = 1280, H = 720;

  public static void main(String[] args) throws Exception {
    if (args.length < 2) { System.err.println("usage: DeckWriter <script> <out.pptx>"); System.exit(2); }
    List<String> lines = readAll(args[0]);
    StringBuilder body = null;
    for (String raw : lines) {
      String line = raw;
      int hash = line.indexOf('#');
      if (hash >= 0) line = line.substring(0, hash);
      if (line.isBlank()) continue;
      String[] t = line.trim().split("\\s+", 2);
      String cmd = t[0];
      String rest = t.length > 1 ? t[1] : "";
      switch (cmd) {
        case "size": {
          String[] wh = rest.trim().split("\\s+");
          W = Integer.parseInt(wh[0]); H = Integer.parseInt(wh[1]);
          break;
        }
        case "slide": {
          if (body != null) bodies.add(body.toString());
          body = new StringBuilder();
          sizes.add(new int[]{W, H});
          media.add(new ArrayList<>());
          slideNo++;
          break;
        }
        case "bg": {
          String c = rest.trim();
          body.append(rect(0, 0, W, H, "F" + c));
          break;
        }
        case "text": {
          int bar = rest.indexOf('|');
          // x y w h size colour font... | content. The font may contain spaces, so it
          // is taken as everything between the colour and the last two fields.
          String head = rest.substring(0, bar).trim();
          String content = rest.substring(bar + 1);
          String[] p = head.split("\\s+");
          String flags = p[p.length - 1];
          int tracking = Integer.parseInt(p[p.length - 2]);
          String font = String.join(" ", Arrays.copyOfRange(p, 6, p.length - 2));
          body.append(text(
            (int) Math.round(Double.parseDouble(p[0])), (int) Math.round(Double.parseDouble(p[1])),
            (int) Math.round(Double.parseDouble(p[2])), (int) Math.round(Double.parseDouble(p[3])),
            (int) Math.round(1000 * Double.parseDouble(p[4])),  // pt -> hundredths
            p[5], font, tracking, flags, content));
          break;
        }
        case "pic": {
          String[] p = rest.trim().split("\\s+");
          String path = rest.trim().substring(
            rest.trim().indexOf(p[4]));
          int id = relId++;
          media.get(media.size() - 1).add(new String[]{String.valueOf(id), path});
          body.append(picture((int) Math.round(Double.parseDouble(p[0])), (int) Math.round(Double.parseDouble(p[1])),
            (int) Math.round(Double.parseDouble(p[2])), (int) Math.round(Double.parseDouble(p[3])), id));
          break;
        }
        default: throw new IllegalArgumentException("unknown directive: " + cmd);
      }
    }
    if (body != null) bodies.add(body.toString());

    write(args[1]);
    System.out.println("deckwriter: " + args[1] + "  " + bodies.size() + " slides");
  }

  /* ── shapes ─────────────────────────────────────────────────────────────── */

  static String xfrm(int x, int y, int w, int h) {
    return "<a:xfrm><a:off x='" + (x * EMU) + "' y='" + (y * EMU) + "'/>" +
           "<a:ext cx='" + (w * EMU) + "' cy='" + (h * EMU) + "'/></a:xfrm>";
  }

  static String rect(int x, int y, int w, int h, String fill) {
    int id = shapeId++;
    return "<p:sp><p:nvSpPr><p:cNvPr id='" + id + "' name='bg" + id + "'/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>" +
      "<p:spPr>" + xfrm(x, y, w, h) + "<a:prstGeom prst='rect'><a:avLst/></a:prstGeom>" +
      "<a:solidFill><a:srgbClr val='" + fill.substring(1) + "'/></a:solidFill><a:ln><a:noFill/></a:ln>" +
      "</p:spPr></p:sp>";
  }

  static String picture(int x, int y, int w, int h, int relId) {
    int id = shapeId++;
    return "<p:pic><p:nvPicPr><p:cNvPr id='" + id + "' name='pic" + id + "'/>" +
      "<p:cNvPicPr><a:picLocks noChangeAspect='1'/></p:cNvPicPr><p:nvPr/></p:nvPicPr>" +
      "<p:blipFill><a:blip r:embed='rId" + relId + "'/><a:stretch><a:fillRect/></a:stretch></p:blipFill>" +
      "<p:spPr>" + xfrm(x, y, w, h) + "<a:prstGeom prst='rect'><a:avLst/></a:prstGeom></p:spPr></p:pic>";
  }

  /** OOXML text: insets to zero so the rect is the type box, not a padded one. */
  static String text(int x, int y, int w, int h, int sz100, String colour, String font,
                     int tracking, String flags, String content) {
    int id = shapeId++;
    boolean bold = flags.contains("B"), italic = flags.contains("I");
    StringBuilder ps = new StringBuilder();
    String[] paras = content.split("\\\\n");
    for (String para : paras) {
      ps.append("<a:p><a:pPr algn='l'><a:lnSpc><a:spcPct val='96000'/></a:lnSpc>")
        .append("<a:spcAft><a:spcPts val='0'/></a:spcAft>")
        .append("<a:buNone/></a:pPr>");
      if (!para.isEmpty()) {
        ps.append("<a:r><a:rPr lang='en-GB' sz='").append(sz100).append("'")
          .append(bold ? " b='1'" : "").append(italic ? " i='1'" : "")
          .append(tracking != 0 ? " spc='" + tracking + "'" : "")
          .append(" dirty='0'><a:solidFill><a:srgbClr val='").append(colour).append("'/></a:solidFill>")
          .append("<a:latin typeface='").append(esc(font)).append("'/>")
          .append("<a:cs typeface='").append(esc(font)).append("'/>")
          .append("</a:rPr><a:t>").append(esc(para)).append("</a:t></a:r>");
      }
      ps.append("<a:endParaRPr lang='en-GB' sz='").append(sz100).append("'/></a:p>");
    }
    return "<p:sp><p:nvSpPr><p:cNvPr id='" + id + "' name='tx" + id + "'/>" +
      "<p:cNvSpPr txBox='1'><a:spLocks noGrp='1'/></p:cNvSpPr><p:nvPr/></p:nvSpPr>" +
      "<p:spPr>" + xfrm(x, y, w, h) + "<a:prstGeom prst='rect'><a:avLst/></a:prstGeom>" +
      "<a:noFill/><a:ln><a:noFill/></a:ln></p:spPr>" +
      "<p:txBody><a:bodyPr wrap='none' lIns='0' tIns='0' rIns='0' bIns='0' anchor='t' anchorCtr='0'/>" +
      "<a:lstStyle/>" + ps + "</p:txBody></p:sp>";
  }

  static String esc(String s) {
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace("'", "&apos;").replace("\"", "&quot;");
  }

  /* ── package ────────────────────────────────────────────────────────────── */

  static void write(String file) throws IOException {
    try (ZipOutputStream zip = new ZipOutputStream(new FileOutputStream(file))) {
      put(zip, "[Content_Types].xml", contentTypes());
      put(zip, "_rels/.rels", rootRels());
      put(zip, "ppt/presentation.xml", presentation());
      put(zip, "ppt/_rels/presentation.xml.rels", presentationRels());
      put(zip, "ppt/presProps.xml", "<p:presentationPr xmlns:a='http://schemas.openxmlformats.org/drawingml/2006/main' xmlns:r='http://schemas.openxmlformats.org/officeDocument/2006/relationships' xmlns:p='http://schemas.openxmlformats.org/presentationml/2006/main'/>");
      put(zip, "ppt/viewProps.xml", "<p:viewPr xmlns:a='http://schemas.openxmlformats.org/drawingml/2006/main' xmlns:r='http://schemas.openxmlformats.org/officeDocument/2006/relationships' xmlns:p='http://schemas.openxmlformats.org/presentationml/2006/main'/>");
      put(zip, "ppt/tableStyles.xml", "<a:tblStyleLst xmlns:a='http://schemas.openxmlformats.org/drawingml/2006/main' def='{5C22544A-7EE6-4342-B048-85BDC9FD1C3A}'/>");
      put(zip, "ppt/theme/theme1.xml", theme());
      put(zip, "ppt/slideMasters/slideMaster1.xml", master());
      put(zip, "ppt/slideMasters/_rels/slideMaster1.xml.rels", masterRels());
      put(zip, "ppt/slideLayouts/slideLayout1.xml", layout());
      put(zip, "ppt/slideLayouts/_rels/slideLayout1.xml.rels", layoutRels());

      for (int i = 0; i < bodies.size(); i++) {
        put(zip, "ppt/slides/slide" + (i + 1) + ".xml", slide(bodies.get(i)));
        put(zip, "ppt/slides/_rels/slide" + (i + 1) + ".xml.rels", slideRels(i));
      }
      // media, de-duplicated by path
      Set<String> seen = new HashSet<>();
      for (List<String[]> per : media) {
        for (String[] m : per) {
          String path = m[1];
          if (seen.add(path)) zip.putNextEntry(new ZipEntry("ppt/media/" + mediaName(path)));
        }
      }
      zip.close();
    }
  }

  static String mediaName(String path) {
    String base = new File(path).getName().replaceAll("[^A-Za-z0-9._-]", "_");
    return base;
  }

  static void put(ZipOutputStream zip, String name, String data) throws IOException {
    zip.putNextEntry(new ZipEntry(name));
    zip.write(data.getBytes("UTF-8"));
    zip.closeEntry();
  }

  static String slide(String shapes) {
    return "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>" +
      "<p:sld xmlns:a='http://schemas.openxmlformats.org/drawingml/2006/main' " +
      "xmlns:r='http://schemas.openxmlformats.org/officeDocument/2006/relationships' " +
      "xmlns:p='http://schemas.openxmlformats.org/presentationml/2006/main'>" +
      "<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id='1' name=''/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>" +
      "<p:grpSpPr><a:xfrm><a:off x='0' y='0'/><a:ext cx='0' cy='0'/><a:chOff x='0' y='0'/><a:chExt cx='0' cy='0'/></a:xfrm></p:grpSpPr>" +
      shapes + "</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>";
  }

  static String slideRels(int i) {
    StringBuilder sb = new StringBuilder("<?xml version='1.0' encoding='UTF-8' standalone='yes'?>" +
      "<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'>" +
      "<Relationship Id='rId1' Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout' Target='../slideLayouts/slideLayout1.xml'/>");
    for (String[] m : media.get(i)) {
      sb.append("<Relationship Id='rId").append(m[0]).append("' Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/image' Target='../media/").append(mediaName(m[1])).append("'/>");
    }
    return sb.append("</Relationships>").toString();
  }

  static String presentation() {
    StringBuilder ids = new StringBuilder();
    for (int i = 0; i < bodies.size(); i++) ids.append("<p:sldId id='").append(256 + i).append("' r:id='rId").append(i + 2).append("'/>");
    return "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>" +
      "<p:presentation xmlns:a='http://schemas.openxmlformats.org/drawingml/2006/main' " +
      "xmlns:r='http://schemas.openxmlformats.org/officeDocument/2006/relationships' " +
      "xmlns:p='http://schemas.openxmlformats.org/presentationml/2006/main'>" +
      "<p:sldMasterIdLst><p:sldMasterId id='2147483648' r:id='rId1'/></p:sldMasterIdLst>" +
      "<p:sldIdLst>" + ids + "</p:sldIdLst>" +
      "<p:sldSz cx='" + (W * EMU) + "' cy='" + (H * EMU) + "'/>" +
      "<p:notesSz cx='6858000' cy='9144000'/>" +
      "<p:defaultTextStyle><a:defPPr><a:defRPr lang='en-GB'/></a:defPPr></p:defaultTextStyle>" +
      "</p:presentation>";
  }

  static String presentationRels() {
    StringBuilder sb = new StringBuilder("<?xml version='1.0' encoding='UTF-8' standalone='yes'?>" +
      "<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'>" +
      "<Relationship Id='rId1' Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster' Target='slideMasters/slideMaster1.xml'/>");
    for (int i = 0; i < bodies.size(); i++) {
      sb.append("<Relationship Id='rId").append(i + 2).append("' Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide' Target='slides/slide").append(i + 1).append(".xml'/>");
    }
    int last = bodies.size() + 3;
    sb.append("<Relationship Id='rId").append(last).append("' Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/presProps' Target='presProps.xml'/>");
    sb.append("<Relationship Id='rId").append(last + 1).append("' Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/viewProps' Target='viewProps.xml'/>");
    sb.append("<Relationship Id='rId").append(last + 2).append("' Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme' Target='theme/theme1.xml'/>");
    sb.append("<Relationship Id='rId").append(last + 3).append("' Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/tableStyles' Target='tableStyles.xml'/>");
    return sb.append("</Relationships>").toString();
  }

  static String masterRels() {
    return "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>" +
      "<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'>" +
      "<Relationship Id='rId1' Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout' Target='../slideLayouts/slideLayout1.xml'/>" +
      "<Relationship Id='rId2' Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme' Target='../theme/theme1.xml'/>" +
      "</Relationships>";
  }

  static String layoutRels() {
    return "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>" +
      "<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'>" +
      "<Relationship Id='rId1' Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster' Target='../slideMasters/slideMaster1.xml'/>" +
      "</Relationships>";
  }

  static String rootRels() {
    return "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>" +
      "<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'>" +
      "<Relationship Id='rId1' Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument' Target='ppt/presentation.xml'/>" +
      "</Relationships>";
  }

  static String contentTypes() {
    StringBuilder sb = new StringBuilder("<?xml version='1.0' encoding='UTF-8' standalone='yes'?>" +
      "<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'>" +
      "<Default Extension='rels' ContentType='application/vnd.openxmlformats-package.relationships+xml'/>" +
      "<Default Extension='xml' ContentType='application/xml'/>" +
      "<Default Extension='png' ContentType='image/png'/>" +
      "<Default Extension='jpg' ContentType='image/jpeg'/>" +
      "<Default Extension='jpeg' ContentType='image/jpeg'/>" +
      "<Override PartName='/ppt/presentation.xml' ContentType='application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml'/>" +
      "<Override PartName='/ppt/slideMasters/slideMaster1.xml' ContentType='application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml'/>" +
      "<Override PartName='/ppt/slideLayouts/slideLayout1.xml' ContentType='application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml'/>" +
      "<Override PartName='/ppt/theme/theme1.xml' ContentType='application/vnd.openxmlformats-officedocument.theme+xml'/>" +
      "<Override PartName='/ppt/presProps.xml' ContentType='application/vnd.openxmlformats-officedocument.presentationml.presProps+xml'/>" +
      "<Override PartName='/ppt/viewProps.xml' ContentType='application/vnd.openxmlformats-officedocument.presentationml.viewProps+xml'/>" +
      "<Override PartName='/ppt/tableStyles.xml' ContentType='application/vnd.openxmlformats-officedocument.presentationml.tableStyles+xml'/>");
    for (int i = 0; i < bodies.size(); i++) {
      sb.append("<Override PartName='/ppt/slides/slide").append(i + 1)
        .append(".xml' ContentType='application/vnd.openxmlformats-officedocument.presentationml.slide+xml'/>");
    }
    return sb.append("</Types>").toString();
  }

  static String layout() {
    return "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>" +
      "<p:sldLayout xmlns:a='http://schemas.openxmlformats.org/drawingml/2006/main' " +
      "xmlns:r='http://schemas.openxmlformats.org/officeDocument/2006/relationships' " +
      "xmlns:p='http://schemas.openxmlformats.org/presentationml/2006/main' type='blank' preserve='1'>" +
      "<p:cSld name='Blank'><p:spTree><p:nvGrpSpPr><p:cNvPr id='1' name=''/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>" +
      "<p:grpSpPr><a:xfrm><a:off x='0' y='0'/><a:ext cx='0' cy='0'/><a:chOff x='0' y='0'/><a:chExt cx='0' cy='0'/></a:xfrm></p:grpSpPr>" +
      "</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>";
  }

  static String master() {
    return "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>" +
      "<p:sldMaster xmlns:a='http://schemas.openxmlformats.org/drawingml/2006/main' " +
      "xmlns:r='http://schemas.openxmlformats.org/officeDocument/2006/relationships' " +
      "xmlns:p='http://schemas.openxmlformats.org/presentationml/2006/main'>" +
      "<p:cSld><p:bg><p:bgPr><a:solidFill><a:srgbClr val='0B0C0E'/></a:solidFill><a:effectLst/></p:bgPr></p:bg>" +
      "<p:spTree><p:nvGrpSpPr><p:cNvPr id='1' name=''/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>" +
      "<p:grpSpPr><a:xfrm><a:off x='0' y='0'/><a:ext cx='0' cy='0'/><a:chOff x='0' y='0'/><a:chExt cx='0' cy='0'/></a:xfrm></p:grpSpPr>" +
      "</p:spTree></p:cSld>" +
      "<p:clrMap bg1='dk1' tx1='lt1' bg2='dk2' tx2='lt2' accent1='accent1' accent2='accent2' accent3='accent3' accent4='accent4' accent5='accent5' accent6='accent6' hlink='hlink' folHlink='folHlink'/>" +
      "<p:sldLayoutIdLst><p:sldLayoutId id='2147483649' r:id='rId1'/></p:sldLayoutIdLst>" +
      "<p:txStyles><p:titleStyle><a:lvl1pPr><a:defRPr sz='3200'><a:solidFill><a:srgbClr val='F2EDE4'/></a:solidFill><a:latin typeface='Georgia'/></a:defRPr></a:lvl1pPr></p:titleStyle>" +
      "<p:bodyStyle><a:lvl1pPr><a:defRPr sz='1400'><a:solidFill><a:srgbClr val='A9A398'/></a:solidFill><a:latin typeface='Arial'/></a:defRPr></a:lvl1pPr></p:bodyStyle>" +
      "<p:otherStyle><a:lvl1pPr><a:defRPr sz='1200'><a:solidFill><a:srgbClr val='F2EDE4'/></a:solidFill><a:latin typeface='Arial'/></a:defRPr></a:lvl1pPr></p:otherStyle></p:txStyles>" +
      "</p:sldMaster>";
  }

  static String theme() {
    return "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>" +
      "<a:theme xmlns:a='http://schemas.openxmlformats.org/drawingml/2006/main' name='KILN'>" +
      "<a:themeElements><a:clrScheme name='KILN'>" +
      "<a:dk1><a:srgbClr val='0B0C0E'/></a:dk1><a:lt1><a:srgbClr val='F2EDE4'/></a:lt1>" +
      "<a:dk2><a:srgbClr val='121316'/></a:dk2><a:lt2><a:srgbClr val='C1BBAF'/></a:lt2>" +
      "<a:accent1><a:srgbClr val='D8542A'/></a:accent1><a:accent2><a:srgbClr val='EE7541'/></a:accent2>" +
      "<a:accent3><a:srgbClr val='8A8578'/></a:accent3><a:accent4><a:srgbClr val='55544F'/></a:accent4>" +
      "<a:accent5><a:srgbClr val='26272B'/></a:accent5><a:accent6><a:srgbClr val='F2EDE4'/></a:accent6>" +
      "<a:hlink><a:srgbClr val='EE7541'/></a:hlink><a:folHlink><a:srgbClr val='8A8578'/></a:folHlink>" +
      "</a:clrScheme>" +
      "<a:fontScheme name='KILN'>" +
      "<a:majorFont><a:latin typeface='Instrument Serif'/><a:ea typeface=''/><a:cs typeface=''/></a:majorFont>" +
      "<a:minorFont><a:latin typeface='Inter Tight'/><a:ea typeface=''/><a:cs typeface=''/></a:minorFont>" +
      "</a:fontScheme>" +
      "<a:fmtScheme name='KILN'>" +
      "<a:fillStyleLst><a:solidFill><a:schemeClr val='phClr'/></a:solidFill>" +
      "<a:solidFill><a:schemeClr val='phClr'/></a:solidFill><a:solidFill><a:schemeClr val='phClr'/></a:solidFill></a:fillStyleLst>" +
      "<a:lnStyleLst><a:ln w='9525'><a:solidFill><a:schemeClr val='phClr'/></a:solidFill></a:ln>" +
      "<a:ln w='9525'><a:solidFill><a:schemeClr val='phClr'/></a:solidFill></a:ln>" +
      "<a:ln w='9525'><a:solidFill><a:schemeClr val='phClr'/></a:solidFill></a:ln></a:lnStyleLst>" +
      "<a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle>" +
      "<a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst>" +
      "<a:bgFillStyleLst><a:solidFill><a:schemeClr val='phClr'/></a:solidFill>" +
      "<a:solidFill><a:schemeClr val='phClr'/></a:solidFill><a:solidFill><a:schemeClr val='phClr'/></a:solidFill></a:bgFillStyleLst>" +
      "</a:fmtScheme></a:themeElements></a:theme>";
  }

  static List<String> readAll(String path) throws IOException {
    List<String> out = new ArrayList<>();
    try (BufferedReader r = new BufferedReader(new InputStreamReader(new FileInputStream(path), "UTF-8"))) {
      String line;
      while ((line = r.readLine()) != null) out.add(line);
    }
    return out;
  }
}
