dnl Process this file with autoconf to produce a configure script.
AC_INIT
AC_PREREQ(2.50)
AC_CONFIG_SRCDIR([configure.ac])
AM_INIT_AUTOMAKE(ulubot,0.1)
AM_CONFIG_HEADER(include/config.h)

dnl Checks for programs
AC_PROG_CC
AC_PROG_INSTALL
AC_LANG_C

dnl Checks for header files
AC_HEADER_STDC
AC_CHECK_HEADERS(unistd.h strings.h errno.h)

dnl Checks for typedefs and structures
AC_C_CONST
AC_C_INLINE
AC_TYPE_SIZE_T

dnl Check -Wall flag of GCC
if test "x$GCC" = "xyes"; then
  if test -z "`echo "$CFLAGS" | grep "\-Wall" 2> /dev/null`" ; then
    CFLAGS="$CFLAGS -Wall"
  fi
fi

dnl Checks for functions
AC_CHECK_FUNCS(getopt_long)

dnl i18n
dnl AM_GNU_GETTEXT([external])

dnl iksemel
PKG_CHECK_MODULES(IKSEMEL,iksemel >= 1.2,,exit)
AC_SUBST(IKSEMEL_CFLAGS)
AC_SUBST(IKSEMEL_LIBS)

dnl Generating makefiles
AC_CONFIG_FILES([
Makefile
src/Makefile
include/Makefile
])
AC_OUTPUT
