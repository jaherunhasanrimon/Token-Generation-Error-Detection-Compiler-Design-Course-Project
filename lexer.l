%option noyywrap nodefault yylineno

%{
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

FILE *yyin;
static int comment_start_line = 1;

static void print_token(const char *type, const char *lexeme) {
    printf("%d | %s | %s\n", yylineno, type, lexeme);
}

static void print_error(const char *lexeme) {
    printf("%d | ERROR | %s\n", yylineno, lexeme);
}
%}

%x COMMENT

LETTER      [A-Za-z_]
DIGIT       [0-9]
ID          {LETTER}({LETTER}|{DIGIT})*
INT         {DIGIT}+
FLOAT       {DIGIT}+"."{DIGIT}+
INVALID_ID  ({DIGIT}+{LETTER}({LETTER}|{DIGIT})*)|([$@#]+({LETTER}|{DIGIT}|_)*)
STRING      \"([^\"\\\n]|\\.)*\"
CHAR        \'([^\'\\\n]|\\.)\'
INVALID_CHAR \'([^\'\\\n]|\\.)([^\'\\\n]|\\.)+\'
KEYWORD     int|float|char|if|else|while|for|return|void|main
STD_FUNCTION printf|scanf|fprintf|sprintf|snprintf|puts|gets|fgets|getchar|putchar
REL_OP      ==|!=|<=|>=|<|>
LOGICAL_OP  \&\&|\|\||!

%%

"/*"                    { comment_start_line = yylineno; BEGIN(COMMENT); }
<COMMENT>"*/"           { BEGIN(INITIAL); }
<COMMENT>\n             { }
<COMMENT>.              { }
<COMMENT><<EOF>>        {
                            yylineno = comment_start_line;
                            print_error("Unterminated comment");
                            return 0;
                        }

"//".*                  { print_token("COMMENT", yytext); }
{STRING}                { print_token("STRING", yytext); }
\"([^\"\\\n]|\\.)*      { print_error("Unterminated string"); }
{CHAR}                  { print_token("CHAR_LITERAL", yytext); }
{INVALID_CHAR}          { print_error("Invalid character literal"); }
\'([^\'\\\n]|\\.)*      { print_error("Unterminated character literal"); }

{KEYWORD}               { print_token("KEYWORD", yytext); }
{STD_FUNCTION}          { print_token("FUNCTION", yytext); }
{REL_OP}                { print_token("RELATIONAL_OP", yytext); }
{LOGICAL_OP}            { print_token("LOGICAL_OP", yytext); }
"+"|"-"|"*"|"/"|"="|"%" { print_token("OPERATOR", yytext); }
"("|")"|"{"|"}"|"["|"]"|";"|","|"." { print_token("PUNCTUATION", yytext); }

{FLOAT}                 { print_token("FLOAT", yytext); }
{INT}                   { print_token("INTEGER", yytext); }
{INVALID_ID}            { print_error(yytext); }
{ID}                    { print_token("IDENTIFIER", yytext); }

[ \t\r]+                { }
\n                      { }
.                       { print_error(yytext); }

%%

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "Usage: %s <input-file>\n", argv[0]);
        return 1;
    }

    yyin = fopen(argv[1], "r");
    if (!yyin) {
        perror("Failed to open input file");
        return 1;
    }

    yylex();
    fclose(yyin);
    return 0;
}
