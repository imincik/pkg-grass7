/* start */
int start_mon(const char *, const char *, int, int, int,
	      const char *, int, int);

/* select.c */
int select_mon(const char *);

/* stop.c */
int stop_mon(const char *);

/* list.c */
void list_mon();
void print_list(FILE *);
int check_mon(const char *);
void list_cmd(const char *, FILE *);
