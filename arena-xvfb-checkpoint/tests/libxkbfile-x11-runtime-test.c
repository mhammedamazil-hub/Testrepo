#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <X11/Xlib.h>
#include <X11/XKBlib.h>
#include <X11/extensions/XKBfile.h>

int main(void)
{
    const char *atom_name = "ARENA_XKBFILE_VALIDATION";
    Atom atom;
    char *round_trip;
    XkbDescPtr xkb;
    Status status;

    if (XInitThreads() == 0) {
        fprintf(stderr, "XInitThreads failed\n");
        return 2;
    }

    /* With no Display, this exercises libxkbfile's own atom table. */
    atom = XkbInternAtom(NULL, atom_name, False);
    if (atom == None) {
        fprintf(stderr, "XkbInternAtom(NULL, ...) failed\n");
        return 3;
    }
    round_trip = XkbAtomGetString(NULL, atom);
    if (round_trip == NULL || strcmp(round_trip, atom_name) != 0) {
        fprintf(stderr, "libxkbfile atom round trip failed\n");
        XFree(round_trip);
        return 4;
    }
    XFree(round_trip);

    /* These allocation routines are implemented by libX11 and are the reason
     * libxkbfile declares a genuine Requires.private dependency on x11. */
    xkb = XkbAllocKeyboard();
    if (xkb == NULL) {
        fprintf(stderr, "XkbAllocKeyboard failed\n");
        return 5;
    }
    status = XkbAllocClientMap(xkb, XkbKeyTypesMask, XkbNumRequiredTypes);
    if (status != Success || xkb->map == NULL || xkb->map->types == NULL ||
        xkb->map->size_types < XkbNumRequiredTypes) {
        fprintf(stderr, "XkbAllocClientMap failed, status=%d\n", (int) status);
        XkbFreeKeyboard(xkb, XkbAllComponentsMask, True);
        return 6;
    }
    XkbFreeKeyboard(xkb, XkbAllComponentsMask, True);

    printf("libxkbfile + libX11 runtime: PASS "
           "(atom round trip; XkbAllocKeyboard/XkbAllocClientMap/XkbFreeKeyboard)\n");
    return 0;
}
